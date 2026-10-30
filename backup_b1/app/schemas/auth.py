from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role: str
    user_id: Optional[str] = None
    installation_id: Optional[str] = None


class TokenPayload(BaseModel):
    sub: str
    role: str = "user"
    installation_id: Optional[str] = None
    exp: Optional[int] = None


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, description="Password with minimum 8 characters")
    full_name: Optional[str] = None
    role: str = Field(default="analyst", description="Role: admin, analyst, user")


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime


class ApiKeyCreate(BaseModel):
    name: str = Field(default="Chrome Extension", max_length=100)
    installation_id: str = Field(min_length=8, max_length=64, description="Unique client installation identifier")


class ApiKeyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    installation_id: str
    name: str
    api_key: Optional[str] = Field(None, description="API key (only returned once on creation)")
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime] = None
