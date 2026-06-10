from pydantic import BaseModel

class FeeResponse(BaseModel):
    """Fee calculation response."""
    transaction_type: str
    amount: int
    fee: int
    currency: str = "VND"
