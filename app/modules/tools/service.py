from typing import Optional, Any
from app.modules.tools.schema import BalanceResponse, TransactionDetail, FeesResponse

class ToolService:
    def __init__(self):
        pass

    async def get_balance(self, user_id: str) -> BalanceResponse:
        from app.modules.tools.financial_tools import check_balance
        data = await check_balance(user_id)
        if data is None or "error" in data:
            from app.common.exceptions import NotFoundException
            raise NotFoundException(f"Wallet for user {user_id} not found or error occurred")
        return BalanceResponse(
            user_id=data["user_id"],
            balance=data["balance"],
            currency=data.get("currency", "VND")
        )

    async def get_transaction(self, transaction_id: str, user_id: Optional[str] = None) -> TransactionDetail:
        from app.modules.tools.financial_tools import get_transaction_status
        data = await get_transaction_status(transaction_id, user_id)
            
        if data is None or "error" in data:
            from app.common.exceptions import NotFoundException
            raise NotFoundException(f"Transaction with ID {transaction_id} not found or access denied")
            
        return TransactionDetail(
            transaction_id=data["transaction_id"],
            user_id=data.get("user_id", "unknown"),
            amount=data.get("amount", 0),
            type=data.get("type", "UNKNOWN"),
            status=data.get("status", "FAILED"),
            timestamp=data.get("timestamp", ""),
            currency=data.get("currency", "VND")
        )

    async def get_fees(self, transaction_type: Optional[str] = None, amount: Optional[int] = None) -> Any:
        from app.modules.tools.financial_tools import get_fee
        if transaction_type is not None and amount is not None:
            # Dynamic fee calculation for a specific transaction type and amount
            return get_fee(transaction_type, amount)
            
        # Default static fees response for backward compatibility
        return FeesResponse(
            transfer_fee=0,
            withdrawal_fee=1100,
            deposit_fee=0,
            currency="VND"
        )
