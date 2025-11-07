from pydantic import BaseModel, EmailStr
from typing import Optional, Literal
from datetime import datetime
import uuid


class UserBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    role: Optional[str] = "sales_rep"
    phone: Optional[str] = None


class UserCreate(UserBase):
    password: Optional[str] = None  # Optional for Microsoft SSO users
    microsoft_id: Optional[str] = None
    auth_provider: Literal["local", "microsoft"] = "local"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class MicrosoftSSOLogin(BaseModel):
    """Schema for Microsoft SSO authentication"""
    access_token: str  # Microsoft access token
    email: EmailStr
    microsoft_id: str  # Microsoft user identifier (oid claim)
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserResponse(UserBase):
    id: uuid.UUID
    is_active: bool
    avatar_url: Optional[str] = None
    microsoft_id: Optional[str] = None
    auth_provider: Literal["local", "microsoft"] = "local"
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[str] = None


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


class UserInvite(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    """Request schema for forgot password"""
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    """Response schema for forgot password"""
    message: str
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Request schema for reset password"""
    token: str
    new_password: str


class ResetPasswordResponse(BaseModel):
    """Response schema for reset password"""
    message: str


class UserStats(BaseModel):
    total: int
    active: int
    inactive: int
    roles: dict


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class PasswordReset(BaseModel):
    new_password: str
