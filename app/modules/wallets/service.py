"""Wallets service"""
from typing import List
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.modules.wallets import repository
from app.modules.wallets.schema import WalletCreateRequest
from app.modules.users import service as users_service
from app.common.exceptions import NotFoundException, BadRequestException
from app.common.constants import WalletStatus, Currency

async def create_wallet(db: AsyncIOMotorDatabase, request: WalletCreateRequest) -> dict:
    """
    Handle wallet creation business logic:
    - Verify associated user exists (raises NotFoundException if not).
    - Validate currency is supported.
    - Default initial balance to 0 and status to ACTIVE.
    """
    # 1. Verify user exists
    await users_service.get_user_by_id(db, request.user_id)
    
    # 2. Validate currency (Pydantic validates it, but double check dynamically)
    if request.currency not in Currency:
        raise BadRequestException(
            message=f"Currency '{request.currency}' is not supported.",
            error_code="INVALID_CURRENCY"
        )
        
    # 3. Create wallet
    wallet_data = {
        "user_id": request.user_id,
        "currency": request.currency,
        "balance": 0,
        "status": WalletStatus.ACTIVE.value
    }
    
    return await repository.create_wallet(db, wallet_data)


async def get_wallet_by_id(db: AsyncIOMotorDatabase, wallet_id: str) -> dict:
    """
    Retrieve wallet by ID, raising an exception if not found.
    """
    wallet = await repository.get_wallet_by_id(db, wallet_id)
    if not wallet:
        raise NotFoundException(
            message=f"Wallet with ID {wallet_id} not found"
        )
    return wallet


async def get_wallets_by_user_id(db: AsyncIOMotorDatabase, user_id: str) -> List[dict]:
    """
    Retrieve all wallets of a specific user.
    - Verify user exists first (raises NotFoundException if not).
    """
    # Verify user exists
    await users_service.get_user_by_id(db, user_id)
    
    return await repository.get_wallets_by_user_id(db, user_id)
