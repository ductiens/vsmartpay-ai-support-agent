from fastapi import APIRouter, Query, Depends
from app.common.response import success_response
from app.common.security import get_current_user
from app.modules.transactions.schema import CreateTransactionRequest, TransactionResponse
from app.modules.transactions.service import TransactionsService
from app.modules.users.schema import UserResponse

router = APIRouter(tags=["Transactions"])
transactions_service = TransactionsService()

@router.post("/transactions", status_code=201)
async def create_transaction(
    request: CreateTransactionRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    txn = await transactions_service.create_transaction(request, current_user.user_id)
    return success_response(
        data=txn.model_dump(),
        message="Transaction created successfully",
        status_code=201,
    )

@router.get("/transactions/{transaction_id}")
async def get_transaction(
    transaction_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    txn = await transactions_service.get_transaction(transaction_id, current_user.user_id)
    return success_response(data=txn.model_dump())

@router.get("/users/me/transactions")
async def get_transaction_history_me(
    current_user: UserResponse = Depends(get_current_user),
    limit: int = Query(default=20, ge=1, le=100),
    skip: int = Query(default=0, ge=0),
):
    result = await transactions_service.get_transaction_history(current_user.user_id, limit, skip)
    return success_response(data=result.model_dump())
