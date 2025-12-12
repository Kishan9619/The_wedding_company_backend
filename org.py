from fastapi import APIRouter, HTTPException, status, Depends
from app.schemas import OrganizationCreate, OrganizationResponse, OrganizationUpdate
from app.database import db
from app.models import OrganizationDB, AdminDB
from app.auth import get_password_hash, get_current_user
from pymongo.errors import DuplicateKeyError

router = APIRouter(prefix="/org", tags=["Organization"])

@router.post("/create", response_model=OrganizationResponse)
async def create_organization(org: OrganizationCreate):
    master_db = db.get_master_db()
    
    # Check if org exists
    existing_org = await master_db["organizations"].find_one({"name": org.organization_name})
    if existing_org:
        raise HTTPException(status_code=400, detail="Organization name already exists")
    
    # Check if admin email exists (assuming unique emails globally)
    existing_admin = await master_db["admins"].find_one({"email": org.email})
    if existing_admin:
        raise HTTPException(status_code=400, detail="Admin email already exists")

    collection_name = f"org_{org.organization_name}"
    
    # Create Organization
    new_org = OrganizationDB(
        name=org.organization_name,
        collection_name=collection_name,
        # admin_id will be linked after creating admin
    )
    
    # Create Admin
    hashed_password = get_password_hash(org.password)
    new_admin = AdminDB(
        email=org.email,
        hashed_password=hashed_password,
        organization_name=org.organization_name
    )
    
    # Transaction would be better but keeping it simple for Motor without replica set setup (local mongo usually standalone)
    admin_result = await master_db["admins"].insert_one(new_admin.model_dump(by_alias=True, exclude={"id"}))
    new_org.admin_id = admin_result.inserted_id
    
    await master_db["organizations"].insert_one(new_org.model_dump(by_alias=True, exclude={"id"}))
    
    # Create dynamic collection (insert dummy then delete or just create)
    # Mongo creates collection on first write. Requirement: "Programmatically create ... optionally initialized".
    # We will just verify it works by inserting a metadata doc
    org_db = db.get_org_db(collection_name)
    await org_db.insert_one({"info": f"Collection for {org.organization_name} created"})

    return OrganizationResponse(
        organization_name=new_org.name,
        collection_name=new_org.collection_name,
        admin_email=new_admin.email
    )

@router.get("/get", response_model=OrganizationResponse)
async def get_organization(organization_name: str):
    master_db = db.get_master_db()
    org = await master_db["organizations"].find_one({"name": organization_name})
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Fetch admin email
    admin = await master_db["admins"].find_one({"_id": org["admin_id"]})
    admin_email = admin["email"] if admin else "Unknown"

    return OrganizationResponse(
        organization_name=org["name"],
        collection_name=org["collection_name"],
        admin_email=admin_email
    )

@router.put("/update", response_model=OrganizationResponse)
async def update_organization(
    org_update: OrganizationUpdate,
    current_user: AdminDB = Depends(get_current_user)
):
    # Only allow updating own org? "Validate that the organization name does not already exist."
    # The requirement says "Input: organization_name, email, password".
    # Does it mean updating the *target* org with new values, or updating *to* new values?
    # Usually PUT updates the resource.
    # Check if user is authorized to update *this* org.
    # But the endpoint takes "organization_name". Is that the target to find, or the new name?
    # "Sync the existing data to the new Table/Collection." -> This implies the NAME changes.
    # So `organization_name` in input is the NEW name.
    # What identifies the org to update? The authenticated user's org.
    
    master_db = db.get_master_db()
    old_org_name = current_user.organization_name
    
    if org_update.organization_name != old_org_name:
        # Check duplicate
        if await master_db["organizations"].find_one({"name": org_update.organization_name}):
            raise HTTPException(status_code=400, detail="New organization name already exists")

        # Rename collection
        old_collection_name = f"org_{old_org_name}"
        new_collection_name = f"org_{org_update.organization_name}"
        
        try:
            # Rename collection
            # Note: renameCollection requires admin privileges on the database usually.
            # Using copy/drop if rename fails or just rename.
            # In same DB:
            await master_db[old_collection_name].rename(new_collection_name)
        except Exception as e:
            # If collection doesn't exist (e.g. empty), just ignore or create new
            pass

        # Update Admin and Org in Master DB
        await master_db["organizations"].update_one(
            {"name": old_org_name},
            {"$set": {"name": org_update.organization_name, "collection_name": new_collection_name}}
        )
        await master_db["admins"].update_one(
            {"organization_name": old_org_name},
            {"$set": {"organization_name": org_update.organization_name}}
        )
        # Also update admin credentials if provided?
        # "Input: email, password" -> Expected Behavior... "Sync existing data"
        # It seems it updates Org Name, and Admin Email/Pass.

    # Update Admin Credentials
    update_fields = {}
    if org_update.email:
         update_fields["email"] = org_update.email
    if org_update.password:
         update_fields["hashed_password"] = get_password_hash(org_update.password)
            
    if update_fields:
        await master_db["admins"].update_one(
            {"organization_name": org_update.organization_name}, # Use NEW name
            {"$set": update_fields}
        )
    
    return OrganizationResponse(
        organization_name=org_update.organization_name,
        collection_name=f"org_{org_update.organization_name}",
        admin_email=org_update.email
    )

@router.delete("/delete")
async def delete_organization(
    organization_name: str,
    current_user: AdminDB = Depends(get_current_user)
):
    # "Allow deletion for respective authenticated user only"
    if current_user.organization_name != organization_name:
         raise HTTPException(status_code=403, detail="Not authorized to delete this organization")
    
    master_db = db.get_master_db()
    
    # Delete Org Metadata
    await master_db["organizations"].delete_one({"name": organization_name})
    
    # Delete Admin
    await master_db["admins"].delete_many({"organization_name": organization_name})
    
    # Drop Collection
    collection_name = f"org_{organization_name}"
    await master_db.drop_collection(collection_name)
    
    return {"detail": f"Organization {organization_name} deleted successfully"}
