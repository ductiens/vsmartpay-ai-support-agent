import logging
from app.modules.chat.schema import ChatRequest, ChatResponse
from app.modules.chat.repository import ChatRepository

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self):
        self.repository = ChatRepository()

    async def process_message(self, request: ChatRequest) -> ChatResponse:
        """
        Main chat flow running through LangGraph multi-agent orchestration.
        """
        from app.core.graph import execute_graph
        return await execute_graph(request)

    async def get_user_sessions(self, user_id: str):
        return await self.repository.get_user_sessions(user_id)

    async def get_user_session_history(self, session_id: str, user_id: str):
        from fastapi import HTTPException, status
        session = await self.repository.get_session_by_id(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Phiên hội thoại không tồn tại."
            )
        
        if session.get("user_id") != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền truy cập lịch sử của phiên hội thoại này."
            )
            
        return await self.repository.get_history(session_id)

    async def admin_get_waiting_sessions(self):
        sessions = await self.repository.get_sessions_by_status("WAITING_HUMAN")
        serialized_sessions = []
        for s in sessions:
            s_copy = s.copy()
            if "created_at" in s_copy and hasattr(s_copy["created_at"], "isoformat"):
                s_copy["created_at"] = s_copy["created_at"].isoformat()
            if "updated_at" in s_copy and hasattr(s_copy["updated_at"], "isoformat"):
                s_copy["updated_at"] = s_copy["updated_at"].isoformat()
            serialized_sessions.append(s_copy)
        return serialized_sessions

    async def admin_get_session_history(self, session_id: str):
        from fastapi import HTTPException, status
        session = await self.repository.get_session_by_id(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Phiên hội thoại không tồn tại."
            )
        return await self.repository.get_history(session_id)

    async def admin_send_message(self, session_id: str, message: str, sender: str):
        from fastapi import HTTPException, status
        session = await self.repository.get_session_by_id(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Phiên hội thoại không tồn tại."
            )
            
        # 1. Ghi tin nhắn CSKH với role="assistant" và sender="HUMAN_AGENT"
        await self.repository.log_message(
            session_id=session_id,
            role="assistant",
            content=message,
            sender=sender
        )
        
        # 2. Cập nhật trạng thái session sang HUMAN_ACTIVE
        await self.repository.update_session_status(session_id, "HUMAN_ACTIVE")
        
        return {"session_id": session_id, "status": "HUMAN_ACTIVE"}
