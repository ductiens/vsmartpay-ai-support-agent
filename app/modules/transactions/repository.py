import logging
from typing import Optional, Dict, Any, List
from app.database import get_db

logger = logging.getLogger(__name__)

class TransactionsRepository:
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
            logger.warning("Database not available, skipping transactions index creation.")
            return
        try:
            await db["transactions"].create_index("transaction_id", unique=True)
            await db["transactions"].create_index("user_id")
            await db["transactions"].create_index("idempotency_key", unique=True, sparse=True)
            await db["transactions"].create_index("created_at")
            logger.info("Transactions collection indexes ensured successfully.")
        except Exception as e:
            logger.error(f"Failed to create transactions indexes: {e}")

    @staticmethod
    async def create_transaction(data: Dict[str, Any]) -> None:
        db = TransactionsRepository._get_active_db()
        await db["transactions"].insert_one(data)

    @staticmethod
    async def get_transaction_by_id(transaction_id: str) -> Optional[Dict[str, Any]]:
        db = TransactionsRepository._get_active_db()
        return await db["transactions"].find_one({"transaction_id": transaction_id}, {"_id": 0})

    @staticmethod
    async def get_transactions_by_user_id(user_id: str, limit: int = 20, skip: int = 0) -> List[Dict[str, Any]]:
        db = TransactionsRepository._get_active_db()
        cursor = db["transactions"].find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)

    @staticmethod
    async def count_transactions_by_user_id(user_id: str) -> int:
        db = TransactionsRepository._get_active_db()
        return await db["transactions"].count_documents({"user_id": user_id})

    @staticmethod
    async def get_transaction_by_idempotency_key(idempotency_key: str) -> Optional[Dict[str, Any]]:
        db = TransactionsRepository._get_active_db()
        return await db["transactions"].find_one({"idempotency_key": idempotency_key}, {"_id": 0})
