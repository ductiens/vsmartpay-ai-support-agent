from datetime import datetime
from pydantic import BaseModel, Field

from app.common.constants import Currency, WalletStatus

class CreateWalletRequest(BaseModel):
    currency: Currency = Field(default=Currency.VND, examples=[Currency.VND])

class WalletResponse(BaseModel):
    wallet_id: str
    user_id: str
    balance: int
    currency: Currency = Currency.VND
    status: WalletStatus = WalletStatus.ACTIVE
    created_at: datetime
