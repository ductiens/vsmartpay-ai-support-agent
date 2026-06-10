"""
FastAPI router for Users module.
"""
from fastapi import APIRouter, Depends
from app.common.response import success_response
from app.common.security import get_current_user
from app.modules.users.schema import CreateUserRequest, UserResponse
from app.modules.users.service import UsersService

router = APIRouter(prefix="/users", tags=["Users"])
users_service = UsersService()

@router.post("", response_model=UserResponse, status_code=201)
async def register(request: CreateUserRequest):
    """
    Đăng ký người dùng demo mới (Public).
    Yêu cầu bổ sung trường mật khẩu (password).
    """
    user = await users_service.create_user(request)
    return success_response(
        data=user.model_dump(),
        message="User registered successfully",
        status_code=201,
    )

@router.get("/me", response_model=UserResponse)
async def get_user_me(current_user: UserResponse = Depends(get_current_user)):
    """
    Lấy thông tin tài khoản đang đăng nhập (Protected).
    """
    return success_response(data=current_user.model_dump())
