from fastapi import APIRouter
from app.modules.chat.schema import ChatRequest, ChatResponse
from app.modules.chat.service import ChatService

router = APIRouter(tags=["Chat"])
chat_service = ChatService()

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    return await chat_service.process_message(request)
