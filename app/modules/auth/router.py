from fastapi import APIRouter
from app.common.response import success_response, BaseSuccessResponse
from app.common.security import create_access_token
from app.modules.auth.schema import LoginRequest, TokenResponse
from app.modules.auth.service import AuthService

router = APIRouter(tags=["Auth"])
auth_service = AuthService()

@router.post("/login", response_model=BaseSuccessResponse[TokenResponse])
async def login(request: LoginRequest):
    user = await auth_service.authenticate_user(request.phone, request.password)
    access_token = create_access_token(data={"sub": user.user_id})
    return success_response(
        data={
            "access_token": access_token,
            "token_type": "bearer",
            "user": user.model_dump(),
        },
        message="Login successful",
    )
