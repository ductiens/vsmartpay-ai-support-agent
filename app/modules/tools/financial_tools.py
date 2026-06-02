"""
Financial tools for chatbot integration.
Functions called by LangGraph tool_router_node and legacy ChatService.

These functions query MongoDB (via FinanceRepository) with a JSON file fallback
if the database is not connected or data is not found.
"""
import json
import os
import logging
from typing import Optional, Dict, Any, List

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
        # Safe production-ready check: return None if user not found in mock files
        return None

    def get_transaction_by_id(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        transactions = self._read_json("transactions.json")
        for t in transactions:
            if t.get("transaction_id") == transaction_id:
                return t
        # Safe check: return None
        return None


# Standalone fallback client for JSON file reads
_client = MockWalletClient()


async def check_balance(user_id: str) -> Optional[Dict[str, Any]]:
    """
    check_balance(user_id) - Call FinanceService to get balance.
    Falls back to wallets.json if DB is not available or user wallet is not found.
    """
    try:
        from app.modules.finance.service import FinanceService
        from app.common.exceptions import NotFoundException
        finance_service = FinanceService()
        
        try:
            balance_data = await finance_service.get_balance(user_id)
            # Fetch wallet metadata for status
            wallet_data = await finance_service.get_wallet_by_user(user_id)
            return {
                "user_id": balance_data.user_id,
                "balance": balance_data.balance,
                "currency": balance_data.currency,
                "status": wallet_data.status
            }
        except NotFoundException:
            pass
    except Exception as e:
        logger.warning(f"check_balance via FinanceService failed, falling back to JSON: {e}")

    # Fallback to JSON file
    return _client.get_wallet_by_user_id(user_id)


def get_fee(transaction_type: str, amount: int) -> Dict[str, Any]:
    """
    get_fee(transaction_type, amount) - Returns fee info based on FinanceService static fee calculation.
    """
    try:
        from app.modules.finance.service import FinanceService
        fee = FinanceService.calculate_fee(transaction_type, amount)
    except Exception as e:
        logger.warning(f"get_fee via FinanceService failed, falling back to local logic: {e}")
        fee = 1100 if transaction_type.upper() == "WITHDRAWAL" else 0

    return {
        "transaction_type": transaction_type,
        "amount": amount,
        "fee": fee,
        "currency": "VND"
    }


async def get_transaction_status(transaction_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """
    get_transaction_status(transaction_id, user_id) - Query MongoDB transactions collection via FinanceService repository.
    Verifies that the transaction belongs to the calling user_id (sender or recipient).
    Falls back to reading transactions.json if DB is not available.
    """
    try:
        from app.modules.finance.service import FinanceService
        finance_service = FinanceService()
        txn = await finance_service.repo.get_transaction_by_id(transaction_id)
        if txn is not None:
            # Security check: transaction ownership
            if txn.get("user_id") != user_id and txn.get("recipient_user_id") != user_id:
                return {"error": "Bạn không có quyền xem thông tin giao dịch này."}
                
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
        logger.warning(f"get_transaction_status via FinanceService failed, falling back to JSON: {e}")

    # Fallback to JSON file with security check
    transactions = _client._read_json("transactions.json")
    for t in transactions:
        if t.get("transaction_id") == transaction_id:
            if t.get("user_id") != user_id and t.get("recipient_user_id") != user_id:
                return {"error": "Bạn không có quyền xem thông tin giao dịch này."}
            return t
            
    return None


async def get_transaction_history(user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    get_transaction_history(user_id) - Query via FinanceService.
    Falls back to reading transactions.json if DB is not available.
    """
    try:
        from app.modules.finance.service import FinanceService
        from app.common.exceptions import NotFoundException
        finance_service = FinanceService()
        
        try:
            history_data = await finance_service.get_transaction_history(user_id, limit=limit, skip=0)
            result = []
            for txn in history_data.transactions:
                result.append({
                    "transaction_id": txn.transaction_id,
                    "amount": txn.amount,
                    "type": txn.type,
                    "status": txn.status,
                    "timestamp": txn.created_at.isoformat() if hasattr(txn.created_at, "isoformat") else str(txn.created_at),
                    "currency": "VND",
                })
            if result:
                return result
        except NotFoundException:
            pass
    except Exception as e:
        logger.warning(f"get_transaction_history via FinanceService failed, falling back to JSON: {e}")

    # Fallback to JSON file
    all_txns = _client._read_json("transactions.json")
    return [t for t in all_txns if t.get("user_id") == user_id][:limit]


async def get_user_kyc_status(user_id: str) -> str:
    """
    get_user_kyc_status(user_id) - Query via FinanceService.
    Falls back to reading users.json if DB is not available.
    """
    try:
        from app.modules.finance.service import FinanceService
        from app.common.exceptions import NotFoundException
        finance_service = FinanceService()
        
        try:
            user_data = await finance_service.get_user(user_id)
            return user_data.kyc_status
        except NotFoundException:
            pass
    except Exception as e:
        logger.warning(f"get_user_kyc_status via FinanceService failed, falling back to JSON: {e}")

    # Fallback to JSON file
    users = _client._read_json("users.json")
    for u in users:
        if u.get("user_id") == user_id:
            return u.get("kyc_status", "UNVERIFIED")
    return "UNVERIFIED"


async def create_support_ticket(
    user_id: str,
    issue_type: str,
    message: str,
    session_id: Optional[str] = None,
    priority: str = "MEDIUM",
    summary: Optional[str] = None,
    assigned_agent_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    create_support_ticket - Creates support ticket and saves it to MongoDB support_tickets.
    Also writes a copy to escalation_tickets for backward compatibility.
    """
    from app.common.utils import generate_id, now_utc
    from app.database import get_db

    ticket_id = f"tkt_{generate_id()}"
    utc_now = now_utc()
    ticket = {
        "ticket_id": ticket_id,
        "session_id": session_id or "",
        "user_id": user_id,
        "priority": priority,
        "status": "OPEN",
        "summary": summary or f"Yêu cầu hỗ trợ về {issue_type}: {message[:100]}...",
        "assigned_agent_id": assigned_agent_id,
        "issue_type": issue_type,
        "message": message,
        "created_at": utc_now,
    }

    db = get_db()
    if db is not None:
        # Create a copy to prevent inserting _id field into the returned dict
        await db["support_tickets"].insert_one(ticket.copy())
        await db["escalation_tickets"].insert_one(ticket.copy())

    # Format UTC time to string for JSON serialization
    ticket_resp = ticket.copy()
    ticket_resp["created_at"] = utc_now.isoformat()
    return ticket_resp
