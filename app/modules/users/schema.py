from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class CreateUserRequest(BaseModel):
    """Request body to create a new user."""
    full_name: str = Field(..., min_length=1, max_length=200, examples=["Nguyễn Văn A"])
    phone: str = Field(..., min_length=10, max_length=15, examples=["0987654321"])
    email: Optional[str] = Field(None, max_length=200, examples=["vana@example.com"])
    password: str = Field(..., min_length=6, max_length=100, examples=["password123"])

class UserResponse(BaseModel):
    """User information response."""
    user_id: str
    full_name: str
    phone: str
    email: Optional[str] = None
    role: str = "user"
    kyc_status: str = "UNVERIFIED"
    created_at: datetime
