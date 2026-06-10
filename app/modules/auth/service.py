import logging
from app.common.utils import verify_password
from app.common.exceptions import BadRequestException
from app.modules.users.schema import UserResponse
from app.modules.users.repository import UsersRepository

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self) -> None:
        self.users_repo = UsersRepository()

    async def authenticate_user(self, phone: str, password: str) -> UserResponse:
        user = await self.users_repo.get_user_by_phone(phone)
        if user is None:
            raise BadRequestException(
                message="Số điện thoại hoặc mật khẩu không chính xác",
                error_code="INVALID_CREDENTIALS",
            )
        if not verify_password(password, user.get("hashed_password", "")):
            raise BadRequestException(
                message="Số điện thoại hoặc mật khẩu không chính xác",
                error_code="INVALID_CREDENTIALS",
            )
        return UserResponse(**user)
