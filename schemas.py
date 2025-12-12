from pydantic import BaseModel, EmailStr
from typing import Optional

class OrganizationCreate(BaseModel):
    organization_name: str
    email: EmailStr
    password: str

class OrganizationUpdate(BaseModel):
    organization_name: str
    email: EmailStr
    password: str

class OrganizationResponse(BaseModel):
    organization_name: str
    collection_name: str
    admin_email: str

class AdminLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
