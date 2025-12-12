Multi-Tenant Backend Service Implementation Plan
This service will manage organizations in a multi-tenant architecture using MongoDB. It will use a Master Database for metadata and dynamic collections for each organization.

User Review Required
Database Architecture: We are using a single MongoDB instance but dynamic collections (org_<name>) for each tenant.
Organization Update: Changing organization name will trigger a collection rename (or data migration) which can be expensive. For the MVP, we will assume reasonable usage or block renaming if user data is large (but we'll implement the renaming for now).
Proposed Changes
Project Structure
backend/
  app/
    __init__.py
    main.py
    config.py
    database.py
    models.py
    schemas.py
    auth.py
    routers/
      auth.py
      org.py
  requirements.txt
Dependencies
fastapi
uvicorn
motor (Validation: chosen for async MongoDB)
pydantic-settings
pyjwt
passlib[bcrypt]
Application Logic
[NEW] 
config.py
Configuration settings (database URL, secret key, etc.)
[NEW] 
database.py
AsyncIOMotorClient setup.
Helper functions to get master DB and dynamic org collections.
[NEW] 
models.py
Organization model (master DB): name, collection_name, admin_email, etc.
Admin user model (stored in master DB as per requirements "Create an admin user associated with that organization. Store ... Admin user reference"). Correction: The requirement says "Store the following in the Master Database: ... Admin user reference". The admin user itself might be in the Master DB or the Org DB. Usually, for multi-tenant SaaS, admins live in Master DB to login. I will store Admins in Master DB.
[NEW] 
auth.py
Password hashing (bcrypt).
JWT token creation and validation/dependency.
[NEW] 
routers/org.py
POST /org/create: Checks if org exists. Creates org_<name> collection. Creates Admin in Master DB. Stores Org metadata in Master DB.
GET /org/get: Fetches Org metadata.
PUT /org/update: Updates metadata. If name changes, renames collection.
DELETE /org/delete: Deletes Org metadata and drops collection.
[NEW] 
routers/auth.py
POST /admin/login: Verifies credentials, returns JWT.
Verification Plan
Automated Tests
Create a test_main.py using pytest and httpx to run create, read, update, delete flows.
Manual Verification
Run the server uvicorn app.main:app --reload.
Use curl or extensive script to hit endpoints.
