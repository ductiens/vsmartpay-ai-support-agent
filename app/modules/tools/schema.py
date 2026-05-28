from pydantic import BaseModel
from typing import Optional, List

class BalanceResponse(BaseModel):
    user_id: str
    balance: int
    currency: str = "VND"

class TransactionDetail(BaseModel):
    transaction_id: str
    user_id: str
    amount: int
    type: str
    status: str
    timestamp: str
    currency: str = "VND"

class FeesResponse(BaseModel):
    transfer_fee: int
    withdrawal_fee: int
    deposit_fee: int
    currency: str = "VND"
