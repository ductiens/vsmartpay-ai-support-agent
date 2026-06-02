from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from app.common.security import get_current_user, get_current_admin
from app.common.response import success_response
from app.modules.finance.schema import UserResponse
from app.modules.chat.schema import (
    ChatRequest, ChatResponse, ChatSessionResponse, ChatMessageResponse,
    AdminReplyRequest, AssignAgentRequest, UpdateTicketStatusRequest, AdminChatMessageRequest
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


# ──────────────────── Advanced CSKH Dashboard Admin APIs ────────────────────

@router.get("/api/v1/admin/support-tickets/{ticket_id}", response_model=None)
async def admin_get_ticket_detail(
    ticket_id: str,
    current_admin: UserResponse = Depends(get_current_admin)
):
    """
    CSKH Dashboard: Xem thông tin chi tiết của một ticket hỗ trợ (Chỉ dành cho Admin/CSKH).
    """
    from app.modules.tickets.repository import TicketsRepository
    ticket = await TicketsRepository.get_ticket_by_id(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket không tồn tại."
        )
    t_copy = ticket.copy()
    if "created_at" in t_copy and hasattr(t_copy["created_at"], "isoformat"):
        t_copy["created_at"] = t_copy["created_at"].isoformat()
    return success_response(
        data=t_copy,
        message="Lấy thông tin chi tiết ticket thành công."
    )

@router.get("/api/v1/admin/support-tickets/{ticket_id}/messages", response_model=List[ChatMessageResponse])
async def admin_get_ticket_messages(
    ticket_id: str,
    current_admin: UserResponse = Depends(get_current_admin)
):
    """
    CSKH Dashboard: Xem toàn bộ lịch sử chat của phiên liên kết với Ticket hỗ trợ (Chỉ dành cho Admin/CSKH).
    """
    from app.modules.tickets.repository import TicketsRepository
    ticket = await TicketsRepository.get_ticket_by_id(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket không tồn tại."
        )
    session_id = ticket.get("session_id")
    if not session_id:
        return []
    return await chat_service.repository.get_history(session_id)

@router.post("/api/v1/admin/support-tickets/{ticket_id}/assign", response_model=None)
async def admin_assign_ticket(
    ticket_id: str,
    request: Optional[AssignAgentRequest] = None,
    current_admin: UserResponse = Depends(get_current_admin)
):
    """
    CSKH Dashboard: Phân công nhân viên CSKH xử lý ticket (Chỉ dành cho Admin/CSKH).
    """
    from app.modules.tickets.repository import TicketsRepository
    ticket = await TicketsRepository.get_ticket_by_id(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket không tồn tại."
        )
    agent_id = (request.assigned_agent_id if request else None) or current_admin.user_id
    await TicketsRepository.assign_ticket_agent(ticket_id, agent_id)
    return success_response(
        data={"ticket_id": ticket_id, "assigned_agent_id": agent_id},
        message="Phân công nhân viên xử lý thành công."
    )

@router.post("/api/v1/admin/support-tickets/{ticket_id}/status", response_model=None)
async def admin_update_ticket_status(
    ticket_id: str,
    request: UpdateTicketStatusRequest,
    current_admin: UserResponse = Depends(get_current_admin)
):
    """
    CSKH Dashboard: Cập nhật trạng thái xử lý ticket (Chỉ dành cho Admin/CSKH).
    """
    from app.modules.tickets.repository import TicketsRepository
    ticket = await TicketsRepository.get_ticket_by_id(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket không tồn tại."
        )
    status_val = request.status.upper()
    await TicketsRepository.update_ticket_status(ticket_id, status_val)
    return success_response(
        data={"ticket_id": ticket_id, "status": status_val},
        message="Cập nhật trạng thái ticket thành công."
    )

@router.post("/api/v1/admin/chat-sessions/{session_id}/messages", response_model=None)
async def admin_send_message(
    session_id: str,
    request: AdminChatMessageRequest,
    current_admin: UserResponse = Depends(get_current_admin)
):
    """
    CSKH Dashboard: Nhân viên CSKH gửi tin nhắn vào phiên chat (Chỉ dành cho Admin/CSKH).
    Tự động cập nhật trạng thái session sang HUMAN_ACTIVE và các ticket OPEN sang PENDING.
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
    
    # 3. Cập nhật các ticket OPEN liên quan sang PENDING và ghi nhận assigned_agent_id
    from app.modules.tickets.repository import TicketsRepository
    await TicketsRepository.update_tickets_status_by_session_id(
        session_id=session_id,
        status="PENDING",
        assigned_agent_id=current_admin.user_id
    )
    
    return success_response(
        data={"session_id": session_id, "status": "HUMAN_ACTIVE"},
        message="Gửi tin nhắn CSKH thành công."
    )
