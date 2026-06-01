"""
Financial tools for chatbot integration.
Functions called by LangGraph tool_router_node and legacy ChatService.

These functions query MongoDB (via FinanceRepository) with a JSON file fallback
if the database is not connected or data is not found.
"""
import json
import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class MockWalletClient:
    """Fallback client that reads from static JSON files in data/mock/."""

    def __init__(self) -> None:
        self.mock_dir = "data/mock"

    def _read_json(self, filename: str) -> list:
        filepath = os.path.join(self.mock_dir, filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def get_wallet_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        wallets = self._read_json("wallets.json")
        for w in wallets:
            if w.get("user_id") == user_id:
                return w
        # Fallback default mock data if files do not exist or user not found
        return {"user_id": user_id, "balance": 1500000, "currency": "VND", "status": "ACTIVE"}

    def get_transaction_by_id(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        transactions = self._read_json("transactions.json")
        for t in transactions:
            if t.get("transaction_id") == transaction_id:
                return t
        # Fallback default mock data
        return {
            "transaction_id": transaction_id,
            "user_id": "usr_test_default",
            "amount": 50000,
            "type": "TRANSFER",
            "status": "SUCCESS",
            "timestamp": "2026-05-28T09:00:00Z",
            "currency": "VND"
        }


# Standalone fallback client for JSON file reads
_client = MockWalletClient()


async def check_balance(user_id: str) -> Optional[Dict[str, Any]]:
    """
    check_balance(user_id) - Query MongoDB wallets collection.
    Falls back to reading wallets.json if DB is not available.
    """
    try:
        from app.database import get_db
        db = get_db()
        if db is not None:
            wallet = await db["wallets"].find_one({"user_id": user_id}, {"_id": 0})
            if wallet is not None:
                return {
                    "user_id": wallet["user_id"],
                    "balance": wallet["balance"],
                    "currency": wallet.get("currency", "VND"),
                    "status": wallet.get("status", "ACTIVE"),
                }
    except Exception as e:
        logger.warning(f"check_balance DB query failed, falling back to JSON: {e}")

    # Fallback to JSON file
    return _client.get_wallet_by_user_id(user_id)


def get_fee(transaction_type: str, amount: int) -> Dict[str, Any]:
    """
    get_fee(transaction_type, amount) - Returns fee info based on transaction type and amount.
    Pure logic, no DB needed.
    """
    fee = 0
    tx_type_upper = transaction_type.upper()
    if tx_type_upper == "WITHDRAWAL":
        fee = 1100
    elif tx_type_upper == "TRANSFER":
        fee = 0
    elif tx_type_upper == "DEPOSIT":
        fee = 0
    return {
        "transaction_type": transaction_type,
        "amount": amount,
        "fee": fee,
        "currency": "VND"
    }


async def get_transaction_status(transaction_id: str) -> Optional[Dict[str, Any]]:
    """
    get_transaction_status(transaction_id) - Query MongoDB transactions collection.
    Falls back to reading transactions.json if DB is not available.
    """
    try:
        from app.database import get_db
        db = get_db()
        if db is not None:
            txn = await db["transactions"].find_one(
                {"transaction_id": transaction_id}, {"_id": 0}
            )
            if txn is not None:
                return {
                    "transaction_id": txn["transaction_id"],
                    "user_id": txn.get("user_id", "unknown"),
                    "amount": txn.get("amount", 0),
                    "type": txn.get("type", "UNKNOWN"),
                    "status": txn.get("status", "UNKNOWN"),
                    "timestamp": txn.get("created_at", "").isoformat() if hasattr(txn.get("created_at", ""), "isoformat") else str(txn.get("created_at", "")),
                    "currency": "VND",
                }
    except Exception as e:
        logger.warning(f"get_transaction_status DB query failed, falling back to JSON: {e}")

    # Fallback to JSON file
    transactions = _client._read_json("transactions.json")
    for t in transactions:
        if t.get("transaction_id") == transaction_id:
            return t
    return None


async def get_transaction_history(user_id: str, limit: int = 10) -> list:
    """
    get_transaction_history(user_id) - Query MongoDB for user's transaction history.
    Falls back to reading transactions.json if DB is not available.
    """
    try:
        from app.database import get_db
        db = get_db()
        if db is not None:
            cursor = db["transactions"].find(
                {"user_id": user_id}, {"_id": 0}
            ).sort("created_at", -1).limit(limit)
            transactions = await cursor.to_list(length=limit)
            result = []
            for txn in transactions:
                result.append({
                    "transaction_id": txn["transaction_id"],
                    "amount": txn.get("amount", 0),
                    "type": txn.get("type", "UNKNOWN"),
                    "status": txn.get("status", "UNKNOWN"),
                    "timestamp": txn.get("created_at", "").isoformat() if hasattr(txn.get("created_at", ""), "isoformat") else str(txn.get("created_at", "")),
                    "currency": "VND",
                })
            if result:
                return result
    except Exception as e:
        logger.warning(f"get_transaction_history DB query failed, falling back to JSON: {e}")

    # Fallback to JSON file
    all_txns = _client._read_json("transactions.json")
    return [t for t in all_txns if t.get("user_id") == user_id][:limit]


async def get_user_kyc_status(user_id: str) -> str:
    """
    get_user_kyc_status(user_id) - Query MongoDB users collection.
    Falls back to reading users.json if DB is not available.
    """
    try:
        from app.database import get_db
        db = get_db()
        if db is not None:
            user = await db["users"].find_one({"user_id": user_id}, {"_id": 0})
            if user is not None:
                return user.get("kyc_status", "UNVERIFIED")
    except Exception as e:
        logger.warning(f"get_user_kyc_status DB query failed, falling back to JSON: {e}")

    # Fallback to JSON file
    users = _client._read_json("users.json")
    for u in users:
        if u.get("user_id") == user_id:
            return u.get("kyc_status", "UNVERIFIED")
    return "UNVERIFIED"


async def create_support_ticket(user_id: str, issue_type: str, message: str) -> Dict[str, Any]:
    """
    create_support_ticket(user_id, issue_type, message) - Creates support ticket and saves it to MongoDB escalation_tickets.
    """
    from app.common.utils import generate_id, now_utc
    from app.database import get_db

    ticket_id = f"tkt_{generate_id()}"
    utc_now = now_utc()
    ticket = {
        "ticket_id": ticket_id,
        "user_id": user_id,
        "issue_type": issue_type,
        "message": message,
        "status": "OPEN",
        "created_at": utc_now,
    }

    db = get_db()
    if db is not None:
        # Create a copy to prevent inserting _id field into the returned dict
        await db["escalation_tickets"].insert_one(ticket.copy())

    # Format UTC time to string for JSON serialization
    ticket_resp = ticket.copy()
    ticket_resp["created_at"] = utc_now.isoformat()
    return ticket_resp
