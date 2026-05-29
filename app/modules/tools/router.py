from fastapi import APIRouter
from typing import Optional
from app.modules.tools.schema import BalanceResponse, TransactionDetail
from app.modules.tools.service import ToolService

router = APIRouter(prefix="/tools", tags=["Financial Tools"])
tool_service = ToolService()

@router.get("/balance/{user_id}", response_model=BalanceResponse)
async def get_balance(user_id: str):
    return await tool_service.get_balance(user_id)

@router.get("/transactions/{transaction_id}", response_model=TransactionDetail)
async def get_transaction(transaction_id: str):
    return await tool_service.get_transaction(transaction_id)

@router.get("/fees")
async def get_fees(transaction_type: Optional[str] = None, amount: Optional[int] = None):
    return await tool_service.get_fees(transaction_type, amount)
