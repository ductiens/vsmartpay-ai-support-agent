"""Ledger router"""
from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List

from app.database import get_db
from app.common.response import success_response
from app.modules.ledger.schema import LedgerEntryResponse
from app.modules.ledger import service

router = APIRouter(prefix="/ledger", tags=["Ledger"])


@router.get("/wallets/{wallet_id}")
async def list_wallet_ledger_entries(
    wallet_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Retrieve all ledger entries associated with a specific wallet ID.
    """
    entries = await service.get_entries_by_wallet_id(db, wallet_id)
    response_data = [LedgerEntryResponse.model_validate(e).model_dump() for e in entries]
    return success_response(
        data=response_data,
        message="Wallet ledger entries retrieved successfully"
    )


@router.get("/transactions/{transaction_id}")
async def list_transaction_ledger_entries(
    transaction_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Retrieve all ledger entries associated with a specific transaction ID.
    """
    entries = await service.get_entries_by_transaction_id(db, transaction_id)
    response_data = [LedgerEntryResponse.model_validate(e).model_dump() for e in entries]
    return success_response(
        data=response_data,
        message="Transaction ledger entries retrieved successfully"
    )
