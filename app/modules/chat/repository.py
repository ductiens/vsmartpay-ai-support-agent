from app.database import get_db
from typing import List, Dict, Any

class ChatRepository:
    def __init__(self):
        # Database connection will be lazily loaded
        pass

    @property
    def collection(self):
        db = get_db()
        if db is not None:
            return db["chat_sessions"]
        return None

    async def save_message(self, session_id: str, role: str, content: str):
        col = self.collection
        if col is not None:
            await col.update_one(
                {"session_id": session_id},
                {"$push": {"history": {"role": role, "content": content}}},
                upsert=True
            )

    async def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        col = self.collection
        if col is not None:
            doc = await col.find_one({"session_id": session_id})
            if doc:
                return doc.get("history", [])
        return []
