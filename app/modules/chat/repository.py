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

    async def log_session(self, session_id: str, user_id: str):
        """Log or update metadata of a chat session."""
        col = self.sessions_collection
        if col is not None:
            utc_now = now_utc()
            await col.update_one(
                {"session_id": session_id},
                {
                    "$set": {
                        "user_id": user_id,
                        "updated_at": utc_now
                    },
                    "$setOnInsert": {
                        "created_at": utc_now
                    }
                },
                upsert=True
            )

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
                    "content": doc.get("content")
                })
            return history
        return []
