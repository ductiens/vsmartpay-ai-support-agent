"""
Financial tools for chatbot integration.
Functions called by LangGraph tool_router_node and legacy ChatService.

These functions query MongoDB to retrieve financial data.
If the database is not connected or data is not found, they return a generic error message.
"""
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


async def check_balance(user_id: str) -> Optional[Dict[str, Any]]:
    """
    check_balance(user_id) - Call FinanceService to get balance.
    Returns error if DB is not available.
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
            return None
    except Exception as e:
        logger.error(f"check_balance via FinanceService failed: {e}")
        return {"error": "Hệ thống đang bận, vui lòng thử lại sau"}


def get_fee(transaction_type: str, amount: int) -> Dict[str, Any]:
    """
    get_fee(transaction_type, amount) - Returns fee info based on FinanceService static fee calculation.
    """
    try:
        from app.modules.fees.service import FeesService
        fees_service = FeesService()
        fee = fees_service.calculate_fee(transaction_type, amount)
    except Exception as e:
        logger.error(f"get_fee via FinanceService failed: {e}")
        return {"error": "Hệ thống đang bận, vui lòng thử lại sau"}

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
    Returns error if DB is not available.
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
        return None
    except Exception as e:
        logger.error(f"get_transaction_status via FinanceService failed: {e}")
        return {"error": "Hệ thống đang bận, vui lòng thử lại sau"}


async def get_transaction_history(user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    get_transaction_history(user_id) - Query via FinanceService.
    Returns error if DB is not available.
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
            return result
        except NotFoundException:
            return []
    except Exception as e:
        logger.error(f"get_transaction_history via FinanceService failed: {e}")
        return [{"error": "Hệ thống đang bận, vui lòng thử lại sau"}]


async def get_user_kyc_status(user_id: str) -> str:
    """
    get_user_kyc_status(user_id) - Query via FinanceService.
    Returns error if DB is not available.
    """
    try:
        from app.modules.users.service import UsersService
        from app.common.exceptions import NotFoundException
        users_service = UsersService()
        
        try:
            user_data = await users_service.get_user(user_id)
            return user_data.kyc_status
        except NotFoundException:
            return "UNVERIFIED"
    except Exception as e:
        logger.error(f"get_user_kyc_status via FinanceService failed: {e}")
        return "ERROR: Hệ thống đang bận, vui lòng thử lại sau"


async def get_spending_statistics_tool(user_id: str, months: int = 1, category: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    get_spending_statistics_tool(user_id, months, category) - Query via TransactionsService.
    Returns error if DB is not available.
    """
    try:
        from app.modules.transactions.service import TransactionsService
        transactions_service = TransactionsService()
        
        stats = await transactions_service.get_spending_statistics(user_id, months, category)
        
        result: Dict[str, Any] = {
            "timeframe": f"{months} tháng",
            "category_requested": category or "all",
            "spending_by_category": []
        }
        
        total_all_categories = 0
        for item in stats:
            cat_name = item.get("_id") or "Khác"
            total = item.get("total_spent", 0)
            total_all_categories += total
            result["spending_by_category"].append({
                "category": cat_name,
                "total_spent": total
            })
            
        result["total_overall"] = total_all_categories
        return result
    except Exception as e:
        logger.error(f"get_spending_statistics_tool failed: {e}")
        return {"error": "Hệ thống đang bận, vui lòng thử lại sau"}


