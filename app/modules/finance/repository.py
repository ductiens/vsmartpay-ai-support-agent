"""
MongoDB repository for Finance module.
Handles CRUD operations for users, wallets, and transactions collections.
"""
import logging
from typing import Optional, Dict, Any, List

from app.database import get_db

logger = logging.getLogger(__name__)


class FinanceRepository:
    """Async MongoDB data access layer for finance collections."""

    @staticmethod
    def _get_active_db():
        """
        Get the active database connection.
        Raises RuntimeError if connection is not initialized, ensuring type safety.
        """
        db = get_db()
        if db is None:
            raise RuntimeError("Database connection not initialized.")
        return db

    # ──────────────────── Index Management ────────────────────

    @staticmethod
    async def ensure_indexes() -> None:
        """
        Create MongoDB indexes for finance collections.
        Called once during application startup in lifespan.
        """
        db = get_db()
        if db is None:
            logger.warning("Database not available, skipping finance index creation.")
            return

        try:
            # users collection indexes
            await db["users"].create_index("user_id", unique=True)
            await db["users"].create_index("phone")
            await db["users"].create_index("email", sparse=True)

            # wallets collection indexes
            await db["wallets"].create_index("wallet_id", unique=True)
            await db["wallets"].create_index("user_id", unique=True)

            # transactions collection indexes
            await db["transactions"].create_index("transaction_id", unique=True)
            await db["transactions"].create_index("user_id")
            await db["transactions"].create_index("idempotency_key", unique=True, sparse=True)
            await db["transactions"].create_index("created_at")

            logger.info("Finance collection indexes ensured successfully.")
        except Exception as e:
            logger.error(f"Failed to create finance indexes: {e}")

    # ──────────────────── Users ────────────────────

    @staticmethod
    async def create_user(data: Dict[str, Any]) -> None:
        """Insert a new user document into the 'users' collection."""
        db = FinanceRepository._get_active_db()
        await db["users"].insert_one(data)

    @staticmethod
    async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
        """Find a user document by user_id."""
        db = FinanceRepository._get_active_db()
        return await db["users"].find_one({"user_id": user_id}, {"_id": 0})

    @staticmethod
    async def get_user_by_phone(phone: str) -> Optional[Dict[str, Any]]:
        """Find a user document by phone number."""
        db = FinanceRepository._get_active_db()
        return await db["users"].find_one({"phone": phone}, {"_id": 0})

    # ──────────────────── Wallets ────────────────────

    @staticmethod
    async def create_wallet(data: Dict[str, Any]) -> None:
        """Insert a new wallet document into the 'wallets' collection."""
        db = FinanceRepository._get_active_db()
        await db["wallets"].insert_one(data)

    @staticmethod
    async def get_wallet_by_user_id(user_id: str) -> Optional[Dict[str, Any]]:
        """Find a wallet document by user_id."""
        db = FinanceRepository._get_active_db()
        return await db["wallets"].find_one({"user_id": user_id}, {"_id": 0})

    @staticmethod
    async def get_wallet_by_id(wallet_id: str) -> Optional[Dict[str, Any]]:
        """Find a wallet document by wallet_id."""
        db = FinanceRepository._get_active_db()
        return await db["wallets"].find_one({"wallet_id": wallet_id}, {"_id": 0})

    @staticmethod
    async def update_wallet_balance(wallet_id: str, new_balance: int, updated_at: Any) -> None:
        """Update the balance of a wallet."""
        db = FinanceRepository._get_active_db()
        await db["wallets"].update_one(
            {"wallet_id": wallet_id},
            {"$set": {"balance": new_balance, "updated_at": updated_at}}
        )

    # ──────────────────── Transactions ────────────────────

    @staticmethod
    async def create_transaction(data: Dict[str, Any]) -> None:
        """Insert a new transaction document into the 'transactions' collection."""
        db = FinanceRepository._get_active_db()
        await db["transactions"].insert_one(data)

    @staticmethod
    async def get_transaction_by_id(transaction_id: str) -> Optional[Dict[str, Any]]:
        """Find a transaction document by transaction_id."""
        db = FinanceRepository._get_active_db()
        return await db["transactions"].find_one({"transaction_id": transaction_id}, {"_id": 0})

    @staticmethod
    async def get_transactions_by_user_id(
        user_id: str,
        limit: int = 20,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Find transactions for a user, sorted by created_at descending.
        Returns a list of transaction documents.
        """
        db = FinanceRepository._get_active_db()
        cursor = db["transactions"].find(
            {"user_id": user_id},
            {"_id": 0}
        ).sort("created_at", -1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)

    @staticmethod
    async def count_transactions_by_user_id(user_id: str) -> int:
        """Count total transactions for a user."""
        db = FinanceRepository._get_active_db()
        return await db["transactions"].count_documents({"user_id": user_id})

    @staticmethod
    async def get_transaction_by_idempotency_key(idempotency_key: str) -> Optional[Dict[str, Any]]:
        """Find a transaction by idempotency_key to prevent duplicates."""
        db = FinanceRepository._get_active_db()
        return await db["transactions"].find_one({"idempotency_key": idempotency_key}, {"_id": 0})
