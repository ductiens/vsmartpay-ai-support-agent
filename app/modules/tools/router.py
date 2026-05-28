from fastapi import APIRouter, Depends
from app.modules.tools.schema import BalanceResponse, TransactionDetail, FeesResponse
from app.modules.tools.service import ToolService

router = APIRouter(prefix="/tools", tags=["Financial Tools"])
tool_service = ToolService()

@router.get("/balance/{user_id}", response_model=BalanceResponse)
async def get_balance(user_id: str):
    return await tool_service.get_balance(user_id)

@router.get("/transactions/{transaction_id}", response_model=TransactionDetail)
async def get_transaction(transaction_id: str):
    return await tool_service.get_transaction(transaction_id)

@router.get("/fees", response_model=FeesResponse)
async def get_fees():
    return await tool_service.get_fees()
