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
