"""
FastAPI router for Finance module.
Thin route handlers that delegate to FinanceService.
All endpoints except /users (register) and /login are protected via JWT.
"""
from fastapi import APIRouter, Query, Depends
from app.common.response import success_response
from app.common.security import get_current_user, create_access_token
from app.modules.finance.schema import (
    CreateUserRequest,
    CreateTransactionRequest,
    LoginRequest,
    TokenResponse,
    UserResponse,
)
from app.modules.finance.service import FinanceService

router = APIRouter(prefix="/finance", tags=["Finance - Users, Wallets, Transactions"])

finance_service = FinanceService()


# ──────────────────── Authentication & Users ────────────────────

@router.post("/users", response_model=UserResponse, status_code=201)
async def register(request: CreateUserRequest):
    """
    Đăng ký người dùng demo mới (Public).
    Yêu cầu bổ sung trường mật khẩu (password).
    """
    user = await finance_service.create_user(request)
    return success_response(
        data=user.model_dump(),
        message="User registered successfully",
        status_code=201,
    )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """
    Đăng nhập bằng số điện thoại và mật khẩu (Public).
    Trả về Bearer Access Token dùng cho các API sau đó.
    """
    user = await finance_service.authenticate_user(request.phone, request.password)
    access_token = create_access_token(data={"sub": user.user_id})
    return success_response(
        data={
            "access_token": access_token,
            "token_type": "bearer",
            "user": user.model_dump(),
        },
        message="Login successful",
    )


@router.get("/users/me", response_model=UserResponse)
async def get_user_me(current_user: UserResponse = Depends(get_current_user)):
    """
    Lấy thông tin tài khoản đang đăng nhập (Protected).
    """
    return success_response(data=current_user.model_dump())


# ──────────────────── Wallets ────────────────────

@router.get("/users/me/wallet")
async def get_wallet_me(current_user: UserResponse = Depends(get_current_user)):
    """
    Lấy thông tin ví của người dùng đang đăng nhập (Protected).
    """
    wallet = await finance_service.get_wallet_by_user(current_user.user_id)
    return success_response(data=wallet.model_dump())


@router.get("/users/me/balance")
async def get_balance_me(current_user: UserResponse = Depends(get_current_user)):
    """
    Lấy số dư ví của người dùng đang đăng nhập (Protected).
    """
    balance = await finance_service.get_balance(current_user.user_id)
    return success_response(data=balance.model_dump())


# ──────────────────── Transactions ────────────────────

@router.post("/transactions", status_code=201)
async def create_transaction(
    request: CreateTransactionRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Tạo giao dịch mới cho người dùng đang đăng nhập (Protected).
    - DEPOSIT: cộng tiền vào ví user
    - WITHDRAWAL: trừ tiền + phí khỏi ví user
    - TRANSFER: trừ ví gửi, cộng ví nhận (yêu cầu recipient_user_id)
    """
    txn = await finance_service.create_transaction(request, current_user.user_id)
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
    """
    Xem chi tiết một giao dịch (Protected - Chỉ cho phép người gửi hoặc người nhận giao dịch xem).
    """
    txn = await finance_service.get_transaction(transaction_id, current_user.user_id)
    return success_response(data=txn.model_dump())


@router.get("/users/me/transactions")
async def get_transaction_history_me(
    current_user: UserResponse = Depends(get_current_user),
    limit: int = Query(default=20, ge=1, le=100),
    skip: int = Query(default=0, ge=0),
):
    """
    Lịch sử giao dịch của người dùng đang đăng nhập, sắp xếp mới nhất trước (Protected).
    """
    result = await finance_service.get_transaction_history(current_user.user_id, limit, skip)
    return success_response(data=result.model_dump())


# ──────────────────── Fees ────────────────────

@router.get("/fees")
async def get_fees(
    type: str = Query(..., description="Loại giao dịch: DEPOSIT, WITHDRAWAL, TRANSFER"),
    amount: int = Query(..., gt=0, description="Số tiền giao dịch (VND)"),
):
    """
    Tra phí giao dịch theo loại và số tiền (Public).
    """
    fee = await finance_service.get_fee(type, amount)
    return success_response(data=fee.model_dump())
