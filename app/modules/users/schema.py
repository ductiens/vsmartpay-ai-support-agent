"""Users schema"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field

class UserCreateRequest(BaseModel):
    email: EmailStr = Field(..., description="Unique email address of the user")
    password: Optional[str] = Field(None, min_length=6, description="Password of the user, min length 6 characters")
    full_name: Optional[str] = Field(None, max_length=100, description="Full name of the user")


class UserResponse(BaseModel):
    id: str = Field(..., description="Unique user identifier (UUID v7)")
    email: EmailStr = Field(..., description="Email address of the user")
    full_name: Optional[str] = Field(None, description="Full name of the user")
    created_at: datetime = Field(..., description="Timestamp when the user was created")
    updated_at: datetime = Field(..., description="Timestamp when the user was last updated")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }
