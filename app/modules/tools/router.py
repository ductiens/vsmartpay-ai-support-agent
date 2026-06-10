from fastapi import APIRouter
from typing import Optional
from app.common.response import success_response, BaseSuccessResponse
from app.modules.tools.schema import BalanceResponse, TransactionDetail, FeesResponse
from app.modules.tools.service import ToolService

router = APIRouter(prefix="/tools", tags=["Financial Tools"], include_in_schema=False)
tool_service = ToolService()

@router.get("/balance/{user_id}", response_model=BaseSuccessResponse[BalanceResponse])
async def get_balance(user_id: str):
    return success_response(data=await tool_service.get_balance(user_id))

@router.get("/transactions/{transaction_id}", response_model=BaseSuccessResponse[TransactionDetail])
async def get_transaction(transaction_id: str):
    return success_response(data=await tool_service.get_transaction(transaction_id))

@router.get("/fees", response_model=BaseSuccessResponse[FeesResponse])
async def get_fees(transaction_type: Optional[str] = None, amount: Optional[int] = None):
    return success_response(data=await tool_service.get_fees(transaction_type, amount))
