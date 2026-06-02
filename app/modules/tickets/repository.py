import logging
from typing import Optional, Dict, Any, List
from app.database import get_db

logger = logging.getLogger(__name__)

class TicketsRepository:
    """Async MongoDB data access layer for support ticket collection."""

    @staticmethod
    def _get_active_db():
        """
        Get the active database connection.
        Raises RuntimeError if connection is not initialized.
        """
        db = get_db()
        if db is None:
            raise RuntimeError("Database connection not initialized.")
        return db

    @staticmethod
    async def ensure_indexes() -> None:
        """
        Create MongoDB indexes for support_tickets collection.
        Called once during application startup in lifespan.
        """
        db = get_db()
        if db is None:
            logger.warning("Database not available, skipping tickets index creation.")
            return

        try:
            await db["support_tickets"].create_index("ticket_id", unique=True)
            await db["support_tickets"].create_index("session_id")
            await db["support_tickets"].create_index("user_id")
            await db["support_tickets"].create_index("created_at")
            logger.info("Support tickets collection indexes ensured successfully.")
        except Exception as e:
            logger.error(f"Failed to create tickets indexes: {e}")

    @staticmethod
    async def create_ticket(data: Dict[str, Any]) -> None:
        """Insert a new support ticket document into the 'support_tickets' collection."""
        db = TicketsRepository._get_active_db()
        await db["support_tickets"].insert_one(data)

    @staticmethod
    async def get_ticket_by_id(ticket_id: str) -> Optional[Dict[str, Any]]:
        """Find a support ticket document by ticket_id."""
        db = TicketsRepository._get_active_db()
        return await db["support_tickets"].find_one({"ticket_id": ticket_id}, {"_id": 0})

    @staticmethod
    async def get_tickets_by_user_id(user_id: str) -> List[Dict[str, Any]]:
        """
        Find all support tickets for a user, sorted by created_at descending.
        """
        db = TicketsRepository._get_active_db()
        cursor = db["support_tickets"].find(
            {"user_id": user_id},
            {"_id": 0}
        ).sort("created_at", -1)
        return await cursor.to_list(length=100)
