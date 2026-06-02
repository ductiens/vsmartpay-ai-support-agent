from fastapi import APIRouter, Depends, status
from typing import List
from app.common.response import success_response
from app.common.security import get_current_user
from app.modules.finance.schema import UserResponse
from app.modules.tickets.schema import CreateTicketRequest, TicketResponse
from app.modules.tickets.service import TicketsService

router = APIRouter(prefix="/support", tags=["Support Tickets - CSKH"])
tickets_service = TicketsService()

@router.post("/tickets", response_model=None, status_code=201)
async def create_ticket(
    request: CreateTicketRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Tạo mới một ticket hỗ trợ kỹ thuật hoặc khiếu nại (Protected).
    """
    ticket = await tickets_service.create_ticket(current_user.user_id, request)
    # Convert Pydantic model to dict for success_response serialization compatibility
    return success_response(
        data=ticket.model_dump(),
        message="Tạo ticket hỗ trợ thành công.",
        status_code=201
    )

@router.get("/tickets", response_model=None)
async def list_tickets(
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Lấy danh sách tất cả các ticket hỗ trợ của người dùng hiện tại (Protected).
    """
    tickets = await tickets_service.get_user_tickets(current_user.user_id)
    # Serialize datetime object in MongoDB document to ISO format
    serialized_tickets = []
    for t in tickets:
        ticket_copy = t.copy()
        if "created_at" in ticket_copy and hasattr(ticket_copy["created_at"], "isoformat"):
            ticket_copy["created_at"] = ticket_copy["created_at"].isoformat()
        serialized_tickets.append(ticket_copy)
        
    return success_response(
        data=serialized_tickets,
        message="Lấy danh sách ticket thành công."
    )

@router.get("/tickets/{ticket_id}", response_model=None)
async def get_ticket(
    ticket_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Lấy thông tin chi tiết của một ticket cụ thể (Protected).
    Yêu cầu quyền truy cập sở hữu ticket tương ứng.
    """
    ticket = await tickets_service.get_ticket(ticket_id, current_user.user_id)
    ticket_copy = ticket.copy()
    if "created_at" in ticket_copy and hasattr(ticket_copy["created_at"], "isoformat"):
        ticket_copy["created_at"] = ticket_copy["created_at"].isoformat()
        
    return success_response(
        data=ticket_copy,
        message="Lấy thông tin chi tiết ticket thành công."
    )
