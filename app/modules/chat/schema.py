from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class ChatRequest(BaseModel):
    session_id: str
    user_id: str
    message: str

class ChatSource(BaseModel):
    doc_id: str
    chunk_id: str
    title: str
    score: float

class EscalationDetail(BaseModel):
    required: bool
    reason: Optional[str] = None
    priority: Optional[str] = None

class ChatResponse(BaseModel):
    answer: str
    intent: str
    confidence: float
    sources: List[ChatSource] = []
    tool_calls: List[Dict[str, Any]] = []
    escalation: EscalationDetail
