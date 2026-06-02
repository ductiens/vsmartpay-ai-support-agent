from typing import List, Dict, Any, Optional
from app.common.utils import generate_id, now_utc
from app.common.exceptions import NotFoundException, ForbiddenException
from app.modules.tickets.schema import CreateTicketRequest, TicketResponse
from app.modules.tickets.repository import TicketsRepository

class TicketsService:
    def __init__(self):
        self.repo = TicketsRepository()

    async def create_ticket(self, user_id: str, request: CreateTicketRequest) -> TicketResponse:
        """
        Creates a new support ticket in the database.
        """
        ticket_id = f"tkt_{generate_id()}"
        created_at = now_utc()
        
        ticket_data = {
            "ticket_id": ticket_id,
            "session_id": request.session_id,
            "user_id": user_id,
            "priority": request.priority or "MEDIUM",
            "status": "OPEN",
            "summary": request.summary,
            "assigned_agent_id": None,
            "created_at": created_at
        }
        
        # Write to both support_tickets and escalation_tickets collections for full integration
        await self.repo.create_ticket(ticket_data)
        
        # Write a copy to escalation_tickets as well
        db = self.repo._get_active_db()
        await db["escalation_tickets"].insert_one(ticket_data.copy())
        
        return TicketResponse(**ticket_data)

    async def get_ticket(self, ticket_id: str, current_user_id: str) -> Dict[str, Any]:
        """
        Retrieves a specific support ticket by ID.
        Checks ownership and raises ForbiddenException if the user doesn't own it.
        """
        ticket = await self.repo.get_ticket_by_id(ticket_id)
        if not ticket:
            raise NotFoundException(
                message="Ticket hỗ trợ không tồn tại.",
                error_code="TICKET_NOT_FOUND"
            )
            
        if ticket["user_id"] != current_user_id:
            raise ForbiddenException(
                message="Bạn không có quyền truy cập ticket hỗ trợ này.",
                error_code="TICKET_FORBIDDEN"
            )
            
        return ticket

    async def get_user_tickets(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves all support tickets belonging to the given user.
        """
        return await self.repo.get_tickets_by_user_id(user_id)
