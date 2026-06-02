from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.common.security import get_current_user
from app.modules.finance.schema import UserResponse
from app.modules.chat.schema import ChatRequest, ChatResponse, ChatSessionResponse, ChatMessageResponse
from app.modules.chat.service import ChatService

router = APIRouter(tags=["Chat"])
chat_service = ChatService()

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Xác thực tin nhắn chat và lưu trữ theo tài khoản của người dùng.
    """
    request.user_id = current_user.user_id
    return await chat_service.process_message(request)

@router.get("/chat/sessions", response_model=List[ChatSessionResponse])
async def get_sessions(
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Lấy danh sách các phiên chat của người dùng hiện tại, sắp xếp mới nhất trước.
    """
    return await chat_service.repository.get_user_sessions(current_user.user_id)

@router.get("/chat/sessions/{session_id}/history", response_model=List[ChatMessageResponse])
async def get_session_history(
    session_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Lấy chi tiết lịch sử tin nhắn của một phiên chat cụ thể.
    Yêu cầu phiên chat phải thuộc về tài khoản người dùng đang đăng nhập.
    """
    session = await chat_service.repository.get_session_by_id(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phiên hội thoại không tồn tại."
        )
    
    if session["user_id"] != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền truy cập lịch sử của phiên hội thoại này."
        )
        
    return await chat_service.repository.get_history(session_id)
