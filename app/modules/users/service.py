"""
Business logic service for Users module.
"""
import logging
from app.common.utils import generate_id, now_utc, hash_password
from app.common.exceptions import DuplicateRequestException, NotFoundException
from app.modules.users.repository import UsersRepository
from app.modules.users.schema import CreateUserRequest, UserResponse

logger = logging.getLogger(__name__)

class UsersService:
    def __init__(self) -> None:
        self.repo = UsersRepository()

    async def create_user(self, request: CreateUserRequest) -> UserResponse:
        """
        Create a new user.
        - Generates user_id with format "usr_{id}"
        - Checks phone duplication
        - kyc_status defaults to UNVERIFIED
        - Hashes password
        """
        existing_phone = await self.repo.get_user_by_phone(request.phone)
        if existing_phone is not None:
            raise DuplicateRequestException(
                message=f"Số điện thoại '{request.phone}' đã được đăng ký",
                error_code="PHONE_ALREADY_EXISTS",
            )

        utc_now = now_utc()
        user_id = f"usr_{generate_id()}"
        hashed_pw = hash_password(request.password)

        user_doc = {
            "user_id": user_id,
            "full_name": request.full_name,
            "phone": request.phone,
            "email": request.email,
            "role": "user",
            "hashed_password": hashed_pw,
            "kyc_status": "UNVERIFIED",
            "created_at": utc_now,
            "updated_at": utc_now,
        }

        await self.repo.create_user(user_doc)
        logger.info(f"Created user: {user_id}")

        # Automatically create default wallet for new user
        from app.modules.wallets.schema import CreateWalletRequest
        from app.modules.wallets.service import WalletsService
        try:
            wallet_svc = WalletsService()
            await wallet_svc.create_wallet(CreateWalletRequest(currency="VND"), user_id=user_id)
            logger.info(f"Automatically created default wallet for user: {user_id}")
        except Exception as e:
            logger.error(f"Failed to auto-create wallet for user {user_id}: {e}")

        return UserResponse(
            user_id=user_id,
            full_name=request.full_name,
            phone=request.phone,
            email=request.email,
            role="user",
            kyc_status="UNVERIFIED",
            created_at=utc_now,
        )

    async def get_user(self, user_id: str) -> UserResponse:
        """Get user information. Raises NotFoundException if not found."""
        user = await self.repo.get_user_by_id(user_id)
        if user is None:
            raise NotFoundException(
                message=f"User '{user_id}' không tồn tại",
                error_code="USER_NOT_FOUND",
            )
        return UserResponse(**user)
