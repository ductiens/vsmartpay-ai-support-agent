"""
FastAPI router for Fees module.
"""
from fastapi import APIRouter, Query
from app.common.response import success_response
from app.modules.fees.service import FeesService

router = APIRouter(prefix="/fees", tags=["Fees"])
fees_service = FeesService()

@router.get("")
async def get_fees(
    type: str = Query(..., description="Loại giao dịch: DEPOSIT, WITHDRAWAL, TRANSFER"),
    amount: int = Query(..., gt=0, description="Số tiền giao dịch (VND)"),
):
    """
    Tra phí giao dịch theo loại và số tiền (Public).
    """
    fee = await fees_service.get_fee(type, amount)
    return success_response(data=fee.model_dump())
