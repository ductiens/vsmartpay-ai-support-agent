"""
Pydantic v2 schemas for Finance module (User, Wallet, Transaction, Fee).
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


# ──────────────────── Request Schemas ────────────────────

class CreateUserRequest(BaseModel):
    """Request body to create a new user."""
    full_name: str = Field(..., min_length=1, max_length=200, examples=["Nguyễn Văn A"])
    phone: str = Field(..., min_length=10, max_length=15, examples=["0987654321"])
    email: Optional[str] = Field(None, max_length=200, examples=["vana@example.com"])
    password: str = Field(..., min_length=6, max_length=100, examples=["password123"])


class CreateWalletRequest(BaseModel):
    """Request body to create a new wallet for a user."""
    currency: str = Field(default="VND", examples=["VND"])


class CreateTransactionRequest(BaseModel):
    """
    Request body to create a new transaction.
    - DEPOSIT: cộng tiền vào ví user
    - WITHDRAWAL: trừ tiền khỏi ví user
    - TRANSFER: trừ tiền ví người gửi, cộng tiền ví người nhận (yêu cầu recipient_user_id)
    """
    amount: int = Field(..., gt=0, description="Số tiền giao dịch (đơn vị nhỏ nhất, VD: VND)", examples=[100000])
    type: str = Field(..., description="Loại giao dịch: DEPOSIT, WITHDRAWAL, TRANSFER", examples=["DEPOSIT"])
    recipient_user_id: Optional[str] = Field(
        None,
        description="User ID người nhận (bắt buộc khi type=TRANSFER)",
        examples=["usr_002"]
    )
    description: Optional[str] = Field(None, max_length=500, examples=["Nạp tiền vào ví"])
    idempotency_key: Optional[str] = Field(
        None,
        description="Khóa idempotency để tránh giao dịch trùng lặp",
        examples=["idem_deposit_001"]
    )


# ──────────────────── Response Schemas ────────────────────

class UserResponse(BaseModel):
    """User information response."""
    user_id: str
    full_name: str
    phone: str
    email: Optional[str] = None
    role: str = "user"
    kyc_status: str = "UNVERIFIED"
    created_at: datetime


class WalletResponse(BaseModel):
    """Wallet information response."""
    wallet_id: str
    user_id: str
    balance: int
    currency: str = "VND"
    status: str = "ACTIVE"
    created_at: datetime


class BalanceResponse(BaseModel):
    """Simplified balance response for quick lookup."""
    user_id: str
    wallet_id: str
    balance: int
    currency: str = "VND"


class TransactionResponse(BaseModel):
    """Single transaction detail response."""
    transaction_id: str
    user_id: str
    wallet_id: str
    amount: int
    type: str
    status: str
    fee: int = 0
    recipient_user_id: Optional[str] = None
    recipient_wallet_id: Optional[str] = None
    description: Optional[str] = None
    idempotency_key: Optional[str] = None
    created_at: datetime


class TransactionListResponse(BaseModel):
    """Paginated transaction history response."""
    transactions: List[TransactionResponse]
    total: int
    limit: int
    skip: int


class FeeResponse(BaseModel):
    """Fee calculation response."""
    transaction_type: str
    amount: int
    fee: int
    currency: str = "VND"


class LoginRequest(BaseModel):
    """Request body to authenticate a user."""
    phone: str = Field(..., min_length=10, max_length=15, examples=["0987654321"])
    password: str = Field(..., min_length=6, max_length=100, examples=["password123"])


class TokenResponse(BaseModel):
    """JWT Token and user info response."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
