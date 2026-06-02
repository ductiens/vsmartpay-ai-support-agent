from app.database import get_db
from app.common.utils import now_utc
from typing import List, Dict, Any, Optional

class ChatRepository:
    def __init__(self):
        pass

    @property
    def sessions_collection(self):
        db = get_db()
        if db is not None:
            return db["chat_sessions"]
        return None

    @property
    def messages_collection(self):
        db = get_db()
        if db is not None:
            return db["chat_messages"]
        return None

    async def log_session(self, session_id: str, user_id: Optional[str] = None):
        """Log or update metadata of a chat session."""
        col = self.sessions_collection
        if col is not None:
            utc_now = now_utc()
            set_dict: Dict[str, Any] = {"updated_at": utc_now}
            if user_id is not None:
                set_dict["user_id"] = user_id
                
            await col.update_one(
                {"session_id": session_id},
                {
                    "$set": set_dict,
                    "$setOnInsert": {
                        "created_at": utc_now,
                        "status": "BOT_ACTIVE"
                    }
                },
                upsert=True
            )

    async def update_session_status(self, session_id: str, status: str):
        """Cập nhật trạng thái của phiên chat."""
        col = self.sessions_collection
        if col is not None:
            await col.update_one(
                {"session_id": session_id},
                {"$set": {"status": status, "updated_at": now_utc()}}
            )

    async def log_agent_trace(self, trace_data: Dict[str, Any]):
        """Lưu vết chạy chi tiết của AI Agent (tracing/logging) vào MongoDB."""
        db = get_db()
        if db is not None:
            await db["agent_traces"].insert_one(trace_data)

    async def log_message(
        self, 
        session_id: str, 
        role: str, 
        content: str, 
        intent: Optional[str] = None, 
        sources: Optional[List[Dict[str, Any]]] = None
    ):
        """Append a new message log (user or assistant) to chat_messages collection."""
        col = self.messages_collection
        if col is not None:
            utc_now = now_utc()
            message_doc = {
                "session_id": session_id,
                "role": role,
                "content": content,
                "timestamp": utc_now,
                "intent": intent,
                "sources": sources or []
            }
            await col.insert_one(message_doc)

    async def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Retrieve full chat message logs sorted by timestamp."""
        col = self.messages_collection
        if col is not None:
            cursor = col.find({"session_id": session_id}).sort("timestamp", 1)
            history = []
            async for doc in cursor:
                history.append({
                    "role": doc.get("role"),
                    "content": doc.get("content"),
                    "timestamp": doc.get("timestamp"),
                    "intent": doc.get("intent"),
                    "sources": doc.get("sources") or []
                })
            return history
        return []

    async def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Retrieve all chat sessions for a user, sorted by updated_at desc."""
        col = self.sessions_collection
        if col is not None:
            cursor = col.find({"user_id": user_id}).sort("updated_at", -1)
            sessions = []
            async for doc in cursor:
                sessions.append({
                    "session_id": doc.get("session_id"),
                    "user_id": doc.get("user_id"),
                    "created_at": doc.get("created_at"),
                    "updated_at": doc.get("updated_at"),
                    "status": doc.get("status", "BOT_ACTIVE")
                })
            return sessions
        return []

    async def get_session_by_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a session by its session_id."""
        col = self.sessions_collection
        if col is not None:
            doc = await col.find_one({"session_id": session_id})
            if doc:
                return {
                    "session_id": doc.get("session_id"),
                    "user_id": doc.get("user_id"),
                    "created_at": doc.get("created_at"),
                    "updated_at": doc.get("updated_at"),
                    "status": doc.get("status", "BOT_ACTIVE")
                }
        return None
