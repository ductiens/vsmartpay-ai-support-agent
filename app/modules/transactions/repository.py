import logging
from typing import Optional, Dict, Any, List
from app.database import get_db

logger = logging.getLogger(__name__)

class TransactionsRepository:
    def __init__(self):
        pass

    @property
    def collection(self):
        db = get_db()
        if db is None:
            raise RuntimeError("Database connection not initialized.")
        return db["transactions"]

    async def ensure_indexes(self) -> None:
        try:
            await self.collection.create_index("transaction_id", unique=True)
            await self.collection.create_index("wallet_id")
            await self.collection.create_index("idempotency_key", unique=True, sparse=True)
            await self.collection.create_index("created_at")
            logger.info("Transactions collection indexes ensured successfully.")
        except Exception as e:
            logger.error(f"Failed to create transactions indexes: {e}")

    async def create_transaction(self, data: Dict[str, Any]) -> None:
        await self.collection.insert_one(data)

    async def get_transaction_by_id(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        return await self.collection.find_one({"transaction_id": transaction_id}, {"_id": 0})

    async def get_transactions_by_user_id(self, user_id: str, limit: int = 20, skip: int = 0) -> List[Dict[str, Any]]:
        cursor = self.collection.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)

    async def count_transactions_by_user_id(self, user_id: str) -> int:
        return await self.collection.count_documents({"user_id": user_id})

    async def get_transaction_by_idempotency_key(self, key: str) -> Optional[Dict[str, Any]]:
        return await self.collection.find_one({"idempotency_key": key}, {"_id": 0})

    async def update_status(self, transaction_id: str, new_status: str, updated_at: Any) -> None:
        await self.collection.update_one(
            {"transaction_id": transaction_id},
            {"$set": {"status": new_status, "updated_at": updated_at}}
        )
