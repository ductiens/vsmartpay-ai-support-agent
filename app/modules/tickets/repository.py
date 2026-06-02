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

    @staticmethod
    async def get_all_tickets(status: Optional[str] = None, priority: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Find all support tickets in the system, sorted by created_at descending.
        Supports filtering by status and priority.
        """
        db = TicketsRepository._get_active_db()
        query = {}
        if status:
            query["status"] = status
        if priority:
            query["priority"] = priority
            
        cursor = db["support_tickets"].find(query, {"_id": 0}).sort("created_at", -1)
        return await cursor.to_list(length=200)

    @staticmethod
    async def update_tickets_status_by_session_id(session_id: str, status: str, assigned_agent_id: str) -> None:
        """
        Update status and assigned_agent_id of all OPEN support tickets associated with the session_id.
        """
        db = TicketsRepository._get_active_db()
        await db["support_tickets"].update_many(
            {"session_id": session_id, "status": "OPEN"},
            {"$set": {"status": status, "assigned_agent_id": assigned_agent_id}}
        )
        # Also update escalation_tickets for complete synchronization
        await db["escalation_tickets"].update_many(
            {"session_id": session_id, "status": "OPEN"},
            {"$set": {"status": status, "assigned_agent_id": assigned_agent_id}}
        )
