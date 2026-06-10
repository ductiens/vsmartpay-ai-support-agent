import logging
from typing import Optional, Dict, Any
from app.database import get_db

logger = logging.getLogger(__name__)

class WalletsRepository:
    def __init__(self):
        pass

    @property
    def collection(self):
        db = get_db()
        if db is None:
            raise RuntimeError("Database connection not initialized.")
        return db["wallets"]

    async def ensure_indexes(self) -> None:
        try:
            await self.collection.create_index("wallet_id", unique=True)
            await self.collection.create_index("user_id", unique=True)
            logger.info("Wallets collection indexes ensured successfully.")
        except Exception as e:
            logger.error(f"Failed to create wallets indexes: {e}")

    async def create_wallet(self, data: Dict[str, Any]) -> None:
        await self.collection.insert_one(data)

    async def get_wallet_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        return await self.collection.find_one({"user_id": user_id}, {"_id": 0})

    async def get_wallet_by_id(self, wallet_id: str) -> Optional[Dict[str, Any]]:
        return await self.collection.find_one({"wallet_id": wallet_id}, {"_id": 0})

    async def update_wallet_balance(self, wallet_id: str, new_balance: int, updated_at: Any) -> None:
        await self.collection.update_one(
            {"wallet_id": wallet_id},
            {"$set": {"balance": new_balance, "updated_at": updated_at}}
        )
