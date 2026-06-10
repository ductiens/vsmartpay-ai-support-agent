"""
Business logic service for Fees module.
"""
import logging
from app.common.exceptions import BadRequestException
from app.modules.fees.schema import FeeResponse

logger = logging.getLogger(__name__)

from app.common.constants import TransactionType

FEE_TABLE = {
    TransactionType.WITHDRAWAL.value: 1100,
    TransactionType.TRANSFER.value: 0,
    TransactionType.DEPOSIT.value: 0,
}
VALID_TRANSACTION_TYPES = {t.value for t in TransactionType}

class FeesService:
    @staticmethod
    def calculate_fee(transaction_type: str, amount: int) -> int:
        return FEE_TABLE.get(transaction_type.upper(), 0)

    async def get_fee(self, transaction_type: str, amount: int) -> FeeResponse:
        tx_type = transaction_type.upper()
        if tx_type not in VALID_TRANSACTION_TYPES:
            raise BadRequestException(
                message=f"Loại giao dịch '{transaction_type}' không hợp lệ",
                error_code="INVALID_TRANSACTION_TYPE",
            )
        fee = self.calculate_fee(tx_type, amount)
        return FeeResponse(
            transaction_type=tx_type,
            amount=amount,
            fee=fee,
            currency="VND",
        )
