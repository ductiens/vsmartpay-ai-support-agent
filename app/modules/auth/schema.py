from pydantic import BaseModel, Field
from app.modules.users.schema import UserResponse

class LoginRequest(BaseModel):
    phone: str = Field(..., min_length=10, max_length=15, examples=["0987654321"])
    password: str = Field(..., min_length=6, max_length=100, examples=["password123"])

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
