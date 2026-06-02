from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CreateTicketRequest(BaseModel):
    session_id: str
    priority: Optional[str] = "MEDIUM"
    summary: str

class TicketResponse(BaseModel):
    ticket_id: str
    session_id: str
    user_id: str
    priority: str
    status: str
    summary: str
    assigned_agent_id: Optional[str] = None
    created_at: datetime
