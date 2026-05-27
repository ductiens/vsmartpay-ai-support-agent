"""Ledger schemas"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.common.constants import LedgerEntryType, Currency

class LedgerEntryCreate(BaseModel):
    transaction_id: str = Field(..., description="UUID v7 associated with the overall transaction")
    wallet_id: str = Field(..., description="UUID v7 of the wallet being debited or credited")
    entry_type: LedgerEntryType = Field(..., description="Type of entry: DEBIT or CREDIT")
    amount: int = Field(..., gt=0, description="Amount of the entry in integer minor units (must be > 0)")
    currency: Currency = Field(..., description="Currency of the entry")
    description: Optional[str] = Field(None, max_length=255, description="Brief narrative of the entry")


class LedgerEntryResponse(BaseModel):
    id: str = Field(..., description="Unique entry identifier (UUID v7)")
    transaction_id: str = Field(..., description="Associated transaction ID")
    wallet_id: str = Field(..., description="Associated wallet ID")
    entry_type: LedgerEntryType = Field(..., description="Type of entry: DEBIT or CREDIT")
    amount: int = Field(..., description="Amount of the entry in integer minor units")
    currency: Currency = Field(..., description="Currency of the entry")
    description: Optional[str] = Field(None, description="Brief narrative of the entry")
    created_at: datetime = Field(..., description="Timestamp when the entry was recorded")

    class Config:
        from_attributes = True
