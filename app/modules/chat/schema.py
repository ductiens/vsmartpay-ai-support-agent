from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class ChatRequest(BaseModel):
    session_id: str
    user_id: Optional[str] = None
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

class ChatSessionResponse(BaseModel):
    session_id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

class ChatMessageResponse(BaseModel):
    role: str
    content: str
    timestamp: datetime
    intent: Optional[str] = None
    sources: List[Dict[str, Any]] = []
