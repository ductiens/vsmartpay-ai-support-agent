"""
MongoDB repository for Users module.
"""
import logging
from typing import Optional, Dict, Any

from app.database import get_db

logger = logging.getLogger(__name__)

class UsersRepository:
    """Async MongoDB data access layer for users collection."""

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
            logger.warning("Database not available, skipping users index creation.")
            return

        try:
            await db["users"].create_index("user_id", unique=True)
            await db["users"].create_index("phone")
            await db["users"].create_index("email", sparse=True)
            logger.info("Users collection indexes ensured successfully.")
        except Exception as e:
            logger.error(f"Failed to create users indexes: {e}")

    @staticmethod
    async def create_user(data: Dict[str, Any]) -> None:
        db = UsersRepository._get_active_db()
        await db["users"].insert_one(data)

    @staticmethod
    async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
        db = UsersRepository._get_active_db()
        return await db["users"].find_one({"user_id": user_id}, {"_id": 0})

    @staticmethod
    async def get_user_by_phone(phone: str) -> Optional[Dict[str, Any]]:
        db = UsersRepository._get_active_db()
        return await db["users"].find_one({"phone": phone}, {"_id": 0})
