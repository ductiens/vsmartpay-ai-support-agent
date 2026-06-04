from pydantic import BaseModel, PrivateAttr
from typing import List, Optional, Dict, Any
from datetime import datetime

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    _user_id: Optional[str] = PrivateAttr(default=None)

    def __init__(self, **data):
        user_id = data.pop("user_id", None)
        super().__init__(**data)
        self._user_id = user_id

    @property
    def user_id(self) -> Optional[str]:
        return getattr(self, "_user_id", None)

    @user_id.setter
    def user_id(self, value: Optional[str]):
        self._user_id = value

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
    session_id: str
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
    status: str = "BOT_ACTIVE"
    title: Optional[str] = None

class AdminChatMessageRequest(BaseModel):
    message: str
    sender: str = "HUMAN_AGENT"

class ChatMessageResponse(BaseModel):
    role: str
    content: str
    timestamp: datetime
    intent: Optional[str] = None
    sources: List[Dict[str, Any]] = []
