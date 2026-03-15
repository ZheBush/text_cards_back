from enum import Enum

from pydantic import BaseModel, EmailStr
from typing import Optional


class UserRole(str, Enum):
    user = "user"
    manager = "manager"


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: UserRole


class UserResponse(BaseModel):
    id: str
    email: EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    user_id: str