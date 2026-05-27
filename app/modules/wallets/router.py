"""Wallets router"""
from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List

from app.database import get_db
from app.common.response import success_response
from app.modules.wallets.schema import WalletCreateRequest, WalletResponse
from app.modules.wallets import service

router = APIRouter(tags=["Wallets"])


@router.post("/wallets", status_code=status.HTTP_201_CREATED)
async def create_wallet(
    request: WalletCreateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Create a new wallet for a user.
    """
    wallet = await service.create_wallet(db, request)
    response_data = WalletResponse.model_validate(wallet)
    return success_response(
        data=response_data.model_dump(),
        message="Wallet created successfully",
        status_code=status.HTTP_201_CREATED
    )


@router.get("/wallets/{wallet_id}")
async def get_wallet_by_id(
    wallet_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Retrieve wallet information by wallet ID.
    """
    wallet = await service.get_wallet_by_id(db, wallet_id)
    response_data = WalletResponse.model_validate(wallet)
    return success_response(
        data=response_data.model_dump(),
        message="Wallet retrieved successfully"
    )


@router.get("/users/{user_id}/wallets")
async def list_user_wallets(
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Retrieve all wallets of a specific user.
    """
    wallets = await service.get_wallets_by_user_id(db, user_id)
    response_data = [WalletResponse.model_validate(w).model_dump() for w in wallets]
    return success_response(
        data=response_data,
        message="User wallets retrieved successfully"
    )
