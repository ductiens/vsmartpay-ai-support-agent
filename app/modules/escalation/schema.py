from pydantic import BaseModel
from typing import Optional

class EscalationRequest(BaseModel):
    user_id: str
    session_id: str
    reason: str

class EscalationResponse(BaseModel):
    required: bool
    reason: Optional[str] = None
    priority: Optional[str] = None
