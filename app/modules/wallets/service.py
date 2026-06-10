import logging
from app.common.utils import generate_id, now_utc
from app.common.exceptions import DuplicateRequestException, NotFoundException
from app.modules.wallets.repository import WalletsRepository
from app.modules.wallets.schema import CreateWalletRequest, WalletResponse
from app.modules.users.repository import UsersRepository

logger = logging.getLogger(__name__)

class WalletsService:
    def __init__(self) -> None:
        self.repo = WalletsRepository()
        self.users_repo = UsersRepository()

    async def create_wallet(self, request: CreateWalletRequest, user_id: str) -> WalletResponse:
        user = await self.users_repo.get_user_by_id(user_id)
        if user is None:
            raise NotFoundException(
                message=f"User '{user_id}' không tồn tại, không thể tạo ví",
                error_code="USER_NOT_FOUND",
            )

        existing = await self.repo.get_wallet_by_user_id(user_id)
        if existing is not None:
            raise DuplicateRequestException(
                message=f"User '{user_id}' đã có ví",
                error_code="WALLET_ALREADY_EXISTS",
            )

        utc_now = now_utc()
        wallet_id = f"wlt_{generate_id()}"

        wallet_doc = {
            "wallet_id": wallet_id,
            "user_id": user_id,
            "balance": 0,
            "currency": request.currency,
            "status": "ACTIVE",
            "created_at": utc_now,
            "updated_at": utc_now,
        }

        await self.repo.create_wallet(wallet_doc)
        logger.info(f"Created wallet {wallet_id} for user {user_id}")

        return WalletResponse(
            wallet_id=wallet_id,
            user_id=user_id,
            balance=0,
            currency=request.currency,
            status="ACTIVE",
            created_at=utc_now,
        )

    async def get_wallet_by_user(self, user_id: str) -> WalletResponse:
        wallet = await self.repo.get_wallet_by_user_id(user_id)
        if wallet is None:
            raise NotFoundException(
                message=f"Ví của user '{user_id}' không tồn tại",
                error_code="WALLET_NOT_FOUND",
            )
        return WalletResponse(**wallet)
