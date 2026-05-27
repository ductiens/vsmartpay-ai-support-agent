"""Users router"""
from fastapi import APIRouter, Depends, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List

from app.database import get_db
from app.common.response import success_response
from app.modules.users.schema import UserCreateRequest, UserResponse
from app.modules.users import service

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user(
    request: UserCreateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Create a new user.
    """
    user = await service.create_user(db, request)
    response_data = UserResponse.model_validate(user)
    return success_response(
        data=response_data.model_dump(),
        message="User created successfully",
        status_code=status.HTTP_201_CREATED
    )


@router.get("/{user_id}")
async def get_user_by_id(
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Retrieve user information by user ID.
    """
    user = await service.get_user_by_id(db, user_id)
    response_data = UserResponse.model_validate(user)
    return success_response(
        data=response_data.model_dump(),
        message="User retrieved successfully"
    )


@router.get("")
async def list_users(
    skip: int = Query(0, ge=0, description="Number of documents to skip"),
    limit: int = Query(100, ge=1, le=100, description="Max number of documents to return"),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Retrieve a paginated list of users.
    """
    users = await service.list_users(db, skip=skip, limit=limit)
    response_data = [UserResponse.model_validate(u).model_dump() for u in users]
    return success_response(
        data=response_data,
        message="Users retrieved successfully"
    )
