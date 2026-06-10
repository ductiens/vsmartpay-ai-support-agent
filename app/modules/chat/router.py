from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from app.common.security import get_current_user, get_current_admin
from app.common.response import success_response
from app.modules.users.schema import UserResponse
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
    return await chat_service.get_user_sessions(current_user.user_id)

@router.get("/chat/sessions/{session_id}/history", response_model=List[ChatMessageResponse])
async def get_session_history(
    session_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Lấy chi tiết lịch sử tin nhắn của một phiên chat cụ thể.
    Yêu cầu phiên chat phải thuộc về tài khoản người dùng đang đăng nhập.
    """
    return await chat_service.get_user_session_history(session_id, current_user.user_id)


# ──────────────────── CSKH Dashboard (Admin) APIs ────────────────────

@router.get("/api/v1/admin/chat-sessions/waiting", response_model=None)
async def admin_list_waiting_sessions(
    current_admin: UserResponse = Depends(get_current_admin)
):
    """
    CSKH Dashboard: Lấy danh sách các phiên chat có trạng thái WAITING_HUMAN (Chỉ dành cho Admin/CSKH).
    """
    data = await chat_service.admin_get_waiting_sessions()
    return success_response(
        data=data,
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
    return await chat_service.admin_get_session_history(session_id)

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
    data = await chat_service.admin_send_message(session_id, request.message, request.sender)
    return success_response(
        data=data,
        message="Gửi tin nhắn CSKH thành công."
    )
