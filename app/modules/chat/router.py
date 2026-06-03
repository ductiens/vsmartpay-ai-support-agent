from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from app.common.security import get_current_user, get_current_admin
from app.common.response import success_response
from app.modules.finance.schema import UserResponse
from app.modules.chat.schema import (
    ChatRequest, ChatResponse, ChatSessionResponse, ChatMessageResponse,
    AdminChatMessageRequest
)
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


# ──────────────────── CSKH Dashboard (Admin) APIs ────────────────────

@router.get("/api/v1/admin/chat-sessions/waiting", response_model=None)
async def admin_list_waiting_sessions(
    current_admin: UserResponse = Depends(get_current_admin)
):
    """
    CSKH Dashboard: Lấy danh sách các phiên chat có trạng thái WAITING_HUMAN (Chỉ dành cho Admin/CSKH).
    """
    sessions = await chat_service.repository.get_sessions_by_status("WAITING_HUMAN")
    
    serialized_sessions = []
    for s in sessions:
        s_copy = s.copy()
        if "created_at" in s_copy and hasattr(s_copy["created_at"], "isoformat"):
            s_copy["created_at"] = s_copy["created_at"].isoformat()
        if "updated_at" in s_copy and hasattr(s_copy["updated_at"], "isoformat"):
            s_copy["updated_at"] = s_copy["updated_at"].isoformat()
        serialized_sessions.append(s_copy)
        
    return success_response(
        data=serialized_sessions,
        message="Lấy danh sách phiên chat đang chờ CSKH thành công."
    )

@router.get("/api/v1/admin/chat-sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
async def admin_get_session_history(
    session_id: str,
    current_admin: UserResponse = Depends(get_current_admin)
):
    """
    CSKH Dashboard: Xem chi tiết toàn bộ lịch sử tin nhắn của một phiên chat (Chỉ dành cho Admin/CSKH).
    Không giới hạn quyền sở hữu.
    """
    session = await chat_service.repository.get_session_by_id(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phiên hội thoại không tồn tại."
        )
    return await chat_service.repository.get_history(session_id)

@router.post("/api/v1/admin/chat-sessions/{session_id}/messages", response_model=None)
async def admin_send_message(
    session_id: str,
    request: AdminChatMessageRequest,
    current_admin: UserResponse = Depends(get_current_admin)
):
    """
    CSKH Dashboard: Nhân viên CSKH gửi tin nhắn vào phiên chat (Chỉ dành cho Admin/CSKH).
    Tự động cập nhật trạng thái session sang HUMAN_ACTIVE.
    """
    session = await chat_service.repository.get_session_by_id(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phiên hội thoại không tồn tại."
        )
        
    # 1. Ghi tin nhắn CSKH với role="assistant" và sender="HUMAN_AGENT"
    await chat_service.repository.log_message(
        session_id=session_id,
        role="assistant",
        content=request.message,
        sender=request.sender
    )
    
    # 2. Cập nhật trạng thái session sang HUMAN_ACTIVE
    await chat_service.repository.update_session_status(session_id, "HUMAN_ACTIVE")
    
    return success_response(
        data={"session_id": session_id, "status": "HUMAN_ACTIVE"},
        message="Gửi tin nhắn CSKH thành công."
    )
