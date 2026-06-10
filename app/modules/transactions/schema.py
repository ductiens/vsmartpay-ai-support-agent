from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

from app.common.constants import TransactionType, TransactionStatus

class CreateTransactionRequest(BaseModel):
    amount: int = Field(..., gt=0, description="Số tiền giao dịch (đơn vị nhỏ nhất, VD: VND)", examples=[100000])
    type: TransactionType = Field(..., description="Loại giao dịch: DEPOSIT, WITHDRAWAL, TRANSFER", examples=[TransactionType.DEPOSIT])
    recipient_user_id: Optional[str] = Field(None, description="User ID người nhận (bắt buộc khi type=TRANSFER)", examples=["usr_002"])
    description: Optional[str] = Field(None, max_length=500, examples=["Nạp tiền vào ví"])
    idempotency_key: Optional[str] = Field(None, description="Khóa idempotency để tránh giao dịch trùng lặp", examples=["idem_deposit_001"])

class TransactionResponse(BaseModel):
    transaction_id: str
    user_id: str
    wallet_id: str
    amount: int
    type: TransactionType
    status: TransactionStatus
    fee: int = 0
    recipient_user_id: Optional[str] = None
    recipient_wallet_id: Optional[str] = None
    description: Optional[str] = None
    idempotency_key: Optional[str] = None
    created_at: datetime

class TransactionListResponse(BaseModel):
    transactions: List[TransactionResponse]
    total: int
    limit: int
    skip: int
