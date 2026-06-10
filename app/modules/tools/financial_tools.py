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
        from app.modules.wallets.service import WalletsService
        from app.common.exceptions import NotFoundException
        wallets_service = WalletsService()
        
        try:
            wallet_data = await wallets_service.get_wallet_by_user(user_id)
            return {
                "user_id": wallet_data.user_id,
                "balance": wallet_data.balance,
                "currency": wallet_data.currency,
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
        from app.modules.fees.service import FeesService
        fees_service = FeesService()
        fee = fees_service.calculate_fee(transaction_type, amount)
    except Exception as e:
        logger.warning(f"get_fee via FinanceService failed, falling back to local logic: {e}")
        fee = 1100 if transaction_type.upper() == "WITHDRAWAL" else 0

    return {
        "transaction_type": transaction_type,
        "amount": amount,
        "fee": fee,
        "currency": "VND"
    }


async def get_transaction_status(transaction_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    get_transaction_status(transaction_id, user_id) - Query MongoDB transactions collection via FinanceService repository.
    Verifies that the transaction belongs to the calling user_id (sender or recipient) if provided.
    Falls back to reading transactions.json if DB is not available.
    """
    try:
        from app.modules.transactions.service import TransactionsService
        transactions_service = TransactionsService()
        txn = await transactions_service.repo.get_transaction_by_id(transaction_id)
        if txn is not None:
            # Security check: transaction ownership (only if user_id is provided)
            if user_id is not None and txn.get("user_id") != user_id and txn.get("recipient_user_id") != user_id:
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
            if user_id is not None and t.get("user_id") != user_id and t.get("recipient_user_id") != user_id:
                return {"error": "Bạn không có quyền xem thông tin giao dịch này."}
            return t
            
    return None


async def get_transaction_history(user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    get_transaction_history(user_id) - Query via FinanceService.
    Falls back to reading transactions.json if DB is not available.
    """
    try:
        from app.modules.transactions.service import TransactionsService
        from app.common.exceptions import NotFoundException
        transactions_service = TransactionsService()
        
        try:
            history_data = await transactions_service.get_transaction_history(user_id, limit=limit, skip=0)
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
        from app.modules.users.service import UsersService
        from app.common.exceptions import NotFoundException
        users_service = UsersService()
        
        try:
            user_data = await users_service.get_user(user_id)
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



