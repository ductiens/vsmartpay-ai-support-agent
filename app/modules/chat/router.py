from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from app.common.security import get_current_user, get_current_admin
from app.common.response import success_response
from app.modules.finance.schema import UserResponse
from app.modules.chat.schema import ChatRequest, ChatResponse, ChatSessionResponse, ChatMessageResponse, AdminReplyRequest
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

@router.get("/api/v1/admin/support-tickets", response_model=None)
async def admin_list_tickets(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    current_admin: UserResponse = Depends(get_current_admin)
):
    """
    CSKH Dashboard: Lấy danh sách toàn bộ ticket hỗ trợ trong hệ thống (Chỉ dành cho Admin/CSKH).
    Hỗ trợ bộ lọc status và priority.
    """
    from app.modules.tickets.repository import TicketsRepository
    tickets = await TicketsRepository.get_all_tickets(status=status, priority=priority)
    
    serialized_tickets = []
    for t in tickets:
        t_copy = t.copy()
        if "created_at" in t_copy and hasattr(t_copy["created_at"], "isoformat"):
            t_copy["created_at"] = t_copy["created_at"].isoformat()
        serialized_tickets.append(t_copy)
        
    return success_response(
        data=serialized_tickets,
        message="Lấy toàn bộ danh sách ticket thành công."
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

@router.post("/api/v1/admin/chat-sessions/{session_id}/reply", response_model=None)
async def admin_reply_to_chat(
    session_id: str,
    request: AdminReplyRequest,
    current_admin: UserResponse = Depends(get_current_admin)
):
    """
    CSKH Dashboard: Nhân viên CSKH phản hồi trực tiếp vào phiên chat của khách hàng (Chỉ dành cho Admin/CSKH).
    Ghi tin nhắn vai trò assistant, cập nhật trạng thái session thành HUMAN_ACTIVE.
    Đồng thời cập nhật các ticket đang OPEN của session_id này sang PENDING và ghi nhận assigned_agent_id.
    """
    session = await chat_service.repository.get_session_by_id(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phiên hội thoại không tồn tại."
        )
        
    # 1. Ghi tin nhắn phản hồi của nhân viên CSKH
    await chat_service.repository.log_message(
        session_id=session_id,
        role="assistant",
        content=request.message
    )
    
    # 2. Cập nhật trạng thái session sang HUMAN_ACTIVE
    await chat_service.repository.update_session_status(session_id, "HUMAN_ACTIVE")
    
    # 3. Cập nhật trạng thái ticket sang PENDING và gắn assigned_agent_id
    from app.modules.tickets.repository import TicketsRepository
    await TicketsRepository.update_tickets_status_by_session_id(
        session_id=session_id,
        status="PENDING",
        assigned_agent_id=current_admin.user_id
    )
    
    return success_response(
        data={"session_id": session_id, "status": "HUMAN_ACTIVE"},
        message="Gửi phản hồi CSKH thành công."
    )
