"""Wallets schema"""
from datetime import datetime
from pydantic import BaseModel, Field
from app.common.constants import Currency, WalletStatus

class WalletCreateRequest(BaseModel):
    user_id: str = Field(..., description="Associated user ID (UUID v7)")
    currency: Currency = Field(..., description="Currency of the wallet")


class WalletResponse(BaseModel):
    id: str = Field(..., description="Unique wallet identifier (UUID v7)")
    user_id: str = Field(..., description="Associated user ID (UUID v7)")
    currency: Currency = Field(..., description="Currency of the wallet")
    balance: int = Field(..., description="Current balance in minor units (e.g. integer)")
    status: WalletStatus = Field(..., description="Status of the wallet")
    created_at: datetime = Field(..., description="Timestamp when the wallet was created")
    updated_at: datetime = Field(..., description="Timestamp when the wallet was last updated")

    class Config:
        from_attributes = True
