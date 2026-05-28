from app.modules.tools.mock_wallet import MockWalletClient
from app.modules.tools.schema import BalanceResponse, TransactionDetail, FeesResponse

class ToolService:
    def __init__(self):
        self.wallet_client = MockWalletClient()

    async def get_balance(self, user_id: str) -> BalanceResponse:
        data = self.wallet_client.get_wallet_by_user_id(user_id)
        return BalanceResponse(
            user_id=data["user_id"],
            balance=data["balance"],
            currency=data.get("currency", "VND")
        )

    async def get_transaction(self, transaction_id: str) -> TransactionDetail:
        data = self.wallet_client.get_transaction_by_id(transaction_id)
        return TransactionDetail(
            transaction_id=data["transaction_id"],
            user_id=data.get("user_id", "unknown"),
            amount=data.get("amount", 0),
            type=data.get("type", "UNKNOWN"),
            status=data.get("status", "FAILED"),
            timestamp=data.get("timestamp", ""),
            currency=data.get("currency", "VND")
        )

    async def get_fees(self) -> FeesResponse:
        # Static mock fees
        return FeesResponse(
            transfer_fee=0,
            withdrawal_fee=1100,
            deposit_fee=0
        )
