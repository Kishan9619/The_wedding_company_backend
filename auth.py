from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from app.schemas import Token, AdminLogin
from app.database import db
from app.auth import verify_password, create_access_token
from app.models import AdminDB

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.post("/login", response_model=Token)
async def login(form_data: AdminLogin):
    # Requirement: Input email/password via JSON body, but OAuth2 uses form data usually.
    # The requirement says "Input: email, password". I used AdminLogin pydantic model.
    # I should support JSON body as per requirement "Input: email, password".
    # OAuth2PasswordRequestForm expects form-data.
    # To strictly follow requirement "POST /admin/login Input: email, password", I will use AdminLogin body.
    
    master_db = db.get_master_db()
    # Admin can belong to any org. We need to find the user by email.
    # But email might not be unique across orgs? "email (admin email)". 
    # Usually email is unique globally or per org.
    # If same email used for multiple orgs, login is ambiguous without org name.
    # Requirement 5: "Validate the admin credentials. On success, return JWT ... containing Org identifier".
    # This implies 1-to-1 or email is unique. I will assume email is unique globally for admins for simplicity.
    
    user = await master_db["admins"].find_one({"email": form_data.email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        data={"sub": user["email"], "org": user["organization_name"]}
    )
    return {"access_token": access_token, "token_type": "bearer"}
