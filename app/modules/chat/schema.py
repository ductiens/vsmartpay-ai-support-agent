from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class ChatRequest(BaseModel):
    user_id: str
    message: str
    session_id: Optional[str] = "default_session"

class EscalationDetail(BaseModel):
    required: bool
    reason: Optional[str] = None

class ChatResponse(BaseModel):
    answer: str
    intent: str
    sources: List[str] = []
    tool_calls: List[Dict[str, Any]] = []
    escalation: EscalationDetail
