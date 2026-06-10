import logging
from typing import Optional, Dict, Any
from app.database import get_db

logger = logging.getLogger(__name__)

class WalletsRepository:
    @staticmethod
    def _get_active_db():
        db = get_db()
        if db is None:
            raise RuntimeError("Database connection not initialized.")
        return db

    @staticmethod
    async def ensure_indexes() -> None:
        db = get_db()
        if db is None:
            logger.warning("Database not available, skipping wallets index creation.")
            return
        try:
            await db["wallets"].create_index("wallet_id", unique=True)
            await db["wallets"].create_index("user_id", unique=True)
            logger.info("Wallets collection indexes ensured successfully.")
        except Exception as e:
            logger.error(f"Failed to create wallets indexes: {e}")

    @staticmethod
    async def create_wallet(data: Dict[str, Any]) -> None:
        db = WalletsRepository._get_active_db()
        await db["wallets"].insert_one(data)

    @staticmethod
    async def get_wallet_by_user_id(user_id: str) -> Optional[Dict[str, Any]]:
        db = WalletsRepository._get_active_db()
        return await db["wallets"].find_one({"user_id": user_id}, {"_id": 0})

    @staticmethod
    async def get_wallet_by_id(wallet_id: str) -> Optional[Dict[str, Any]]:
        db = WalletsRepository._get_active_db()
        return await db["wallets"].find_one({"wallet_id": wallet_id}, {"_id": 0})

    @staticmethod
    async def update_wallet_balance(wallet_id: str, new_balance: int, updated_at: Any) -> None:
        db = WalletsRepository._get_active_db()
        await db["wallets"].update_one(
            {"wallet_id": wallet_id},
            {"$set": {"balance": new_balance, "updated_at": updated_at}}
        )
