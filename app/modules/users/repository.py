"""
MongoDB repository for Users module.
"""
import logging
from typing import Optional, Dict, Any

from app.database import get_db

logger = logging.getLogger(__name__)

class UsersRepository:
    """Async MongoDB data access layer for users collection."""

    def __init__(self):
        pass

    @property
    def collection(self):
        db = get_db()
        if db is None:
            raise RuntimeError("Database connection not initialized.")
        return db["users"]

    async def ensure_indexes(self) -> None:
        try:
            await self.collection.create_index("user_id", unique=True)
            await self.collection.create_index("phone")
            await self.collection.create_index("email", sparse=True)
            logger.info("Users collection indexes ensured successfully.")
        except Exception as e:
            logger.error(f"Failed to create users indexes: {e}")

    async def create_user(self, data: Dict[str, Any]) -> None:
        await self.collection.insert_one(data)

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        return await self.collection.find_one({"user_id": user_id}, {"_id": 0})

    async def get_user_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        return await self.collection.find_one({"phone": phone}, {"_id": 0})
