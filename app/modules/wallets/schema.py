from datetime import datetime
from pydantic import BaseModel, Field

class CreateWalletRequest(BaseModel):
    currency: str = Field(default="VND", examples=["VND"])

class WalletResponse(BaseModel):
    wallet_id: str
    user_id: str
    balance: int
    currency: str = "VND"
    status: str = "ACTIVE"
    created_at: datetime
