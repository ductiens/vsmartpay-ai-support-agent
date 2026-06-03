"""
Business logic service for Finance module.
Handles user creation, wallet management, transaction processing, and fee calculation.

Business rules (theo AGENTS.md):
- Không dùng float cho tiền → dùng integer VND
- amount > 0 cho mọi giao dịch
- Idempotency cho payment-like APIs
- Transaction status: PENDING → SUCCESS / FAILED
- TRANSFER: trừ ví gửi + cộng ví nhận (yêu cầu recipient_user_id)
"""
import logging
from typing import Optional, List, Dict, Any

from app.common.utils import generate_id, now_utc, hash_password, verify_password
from app.common.exceptions import (
    NotFoundException,
    BadRequestException,
    InsufficientBalanceException,
    DuplicateRequestException,
    ForbiddenException,
)
from app.modules.finance.repository import FinanceRepository
from app.modules.finance.schema import (
    CreateUserRequest,
    CreateWalletRequest,
    CreateTransactionRequest,
    UserResponse,
    WalletResponse,
    BalanceResponse,
    TransactionResponse,
    TransactionListResponse,
    FeeResponse,
)

logger = logging.getLogger(__name__)

# Phí cố định (VND)
FEE_TABLE = {
    "WITHDRAWAL": 1100,
    "TRANSFER": 0,
    "DEPOSIT": 0,
}

VALID_TRANSACTION_TYPES = {"DEPOSIT", "WITHDRAWAL", "TRANSFER"}


class FinanceService:
    """Business logic layer for finance operations."""

    def __init__(self) -> None:
        self.repo = FinanceRepository()

    # ──────────────────── Users ────────────────────

    async def create_user(self, request: CreateUserRequest) -> UserResponse:
        """
        Tạo user mới.
        - Sinh user_id bằng UUID v7 format "usr_{id}"
        - Kiểm tra trùng lặp số điện thoại (phone)
        - kyc_status mặc định = UNVERIFIED
        - Mã hóa mật khẩu bằng bcrypt trước khi lưu trữ
        """
        # Kiểm tra số điện thoại đã tồn tại chưa
        existing_phone = await self.repo.get_user_by_phone(request.phone)
        if existing_phone is not None:
            raise DuplicateRequestException(
                message=f"Số điện thoại '{request.phone}' đã được đăng ký",
                error_code="PHONE_ALREADY_EXISTS",
            )

        utc_now = now_utc()
        user_id = f"usr_{generate_id()}"
        hashed_pw = hash_password(request.password)

        role_val = request.role or "user"
        user_doc = {
            "user_id": user_id,
            "full_name": request.full_name,
            "phone": request.phone,
            "email": request.email,
            "role": role_val,
            "hashed_password": hashed_pw,
            "kyc_status": "UNVERIFIED",
            "created_at": utc_now,
            "updated_at": utc_now,
        }

        await self.repo.create_user(user_doc)
        logger.info(f"Created user: {user_id}")

        # Automatically create default wallet for new user
        from app.modules.finance.schema import CreateWalletRequest
        try:
            await self.create_wallet(CreateWalletRequest(currency="VND"), user_id=user_id)
            logger.info(f"Automatically created default wallet for user: {user_id}")
        except Exception as e:
            logger.error(f"Failed to auto-create wallet for user {user_id}: {e}")

        return UserResponse(
            user_id=user_id,
            full_name=request.full_name,
            phone=request.phone,
            email=request.email,
            role=role_val,
            kyc_status="UNVERIFIED",
            created_at=utc_now,
        )

    async def get_user(self, user_id: str) -> UserResponse:
        """Lấy thông tin user. Raise NotFoundException nếu không tìm thấy."""
        user = await self.repo.get_user_by_id(user_id)
        if user is None:
            raise NotFoundException(
                message=f"User '{user_id}' không tồn tại",
                error_code="USER_NOT_FOUND",
            )
        return UserResponse(**user)

    async def authenticate_user(self, phone: str, password: str) -> UserResponse:
        """
        Xác thực user bằng số điện thoại và mật khẩu.
        Trả về thông tin UserResponse nếu thành công.
        """
        user = await self.repo.get_user_by_phone(phone)
        if user is None:
            raise BadRequestException(
                message="Số điện thoại hoặc mật khẩu không chính xác",
                error_code="INVALID_CREDENTIALS",
            )

        # Kiểm tra mật khẩu
        if not verify_password(password, user.get("hashed_password", "")):
            raise BadRequestException(
                message="Số điện thoại hoặc mật khẩu không chính xác",
                error_code="INVALID_CREDENTIALS",
            )

        return UserResponse(**user)

    # ──────────────────── Wallets ────────────────────

    async def create_wallet(self, request: CreateWalletRequest, user_id: str) -> WalletResponse:
        """
        Tạo ví cho user.
        - Kiểm tra user tồn tại
        - Mỗi user chỉ có 1 ví (unique index trên user_id)
        - Balance khởi tạo = 0
        """
        # Kiểm tra user tồn tại
        user = await self.repo.get_user_by_id(user_id)
        if user is None:
            raise NotFoundException(
                message=f"User '{user_id}' không tồn tại, không thể tạo ví",
                error_code="USER_NOT_FOUND",
            )

        # Kiểm tra user đã có ví chưa
        existing = await self.repo.get_wallet_by_user_id(user_id)
        if existing is not None:
            raise DuplicateRequestException(
                message=f"User '{user_id}' đã có ví",
                error_code="WALLET_ALREADY_EXISTS",
            )

        utc_now = now_utc()
        wallet_id = f"wlt_{generate_id()}"

        wallet_doc = {
            "wallet_id": wallet_id,
            "user_id": user_id,
            "balance": 0,
            "currency": request.currency,
            "status": "ACTIVE",
            "created_at": utc_now,
            "updated_at": utc_now,
        }

        await self.repo.create_wallet(wallet_doc)
        logger.info(f"Created wallet {wallet_id} for user {user_id}")

        return WalletResponse(
            wallet_id=wallet_id,
            user_id=user_id,
            balance=0,
            currency=request.currency,
            status="ACTIVE",
            created_at=utc_now,
        )

    async def get_wallet_by_user(self, user_id: str) -> WalletResponse:
        """Lấy thông tin ví theo user_id."""
        wallet = await self.repo.get_wallet_by_user_id(user_id)
        if wallet is None:
            raise NotFoundException(
                message=f"Ví của user '{user_id}' không tồn tại",
                error_code="WALLET_NOT_FOUND",
            )
        return WalletResponse(**wallet)

    async def get_balance(self, user_id: str) -> BalanceResponse:
        """Lấy số dư ví đơn giản."""
        wallet = await self.repo.get_wallet_by_user_id(user_id)
        if wallet is None:
            raise NotFoundException(
                message=f"Ví của user '{user_id}' không tồn tại",
                error_code="WALLET_NOT_FOUND",
            )
        return BalanceResponse(
            user_id=user_id,
            wallet_id=wallet["wallet_id"],
            balance=wallet["balance"],
            currency=wallet["currency"],
        )

    # ──────────────────── Transactions ────────────────────

    async def create_transaction(self, request: CreateTransactionRequest, user_id: str) -> TransactionResponse:
        """
        Xử lý giao dịch.

        Ví dụ:
        - DEPOSIT 100,000 VND: cộng 100,000 vào ví user
        - WITHDRAWAL 50,000 VND: trừ 50,000 + phí 1,100 khỏi ví user
        - TRANSFER 200,000 VND từ ví gửi → cộng ví nhận (yêu cầu recipient_user_id)
        """
        tx_type = request.type.upper()

        # Validate transaction type
        if tx_type not in VALID_TRANSACTION_TYPES:
            raise BadRequestException(
                message=f"Loại giao dịch '{request.type}' không hợp lệ. Chấp nhận: {', '.join(VALID_TRANSACTION_TYPES)}",
                error_code="INVALID_TRANSACTION_TYPE",
            )

        # TRANSFER yêu cầu recipient_user_id
        if tx_type == "TRANSFER" and not request.recipient_user_id:
            raise BadRequestException(
                message="Giao dịch TRANSFER yêu cầu trường 'recipient_user_id'",
                error_code="MISSING_RECIPIENT",
            )

        # Không cho phép tự chuyển cho chính mình
        if tx_type == "TRANSFER" and request.recipient_user_id == user_id:
            raise BadRequestException(
                message="Không thể chuyển tiền cho chính mình",
                error_code="SELF_TRANSFER",
            )

        # Kiểm tra idempotency_key trùng
        if request.idempotency_key:
            existing_txn = await self.repo.get_transaction_by_idempotency_key(request.idempotency_key)
            if existing_txn is not None:
                raise DuplicateRequestException(
                    message=f"Giao dịch với idempotency_key '{request.idempotency_key}' đã tồn tại",
                    error_code="DUPLICATE_TRANSACTION",
                    details={"existing_transaction_id": existing_txn["transaction_id"]},
                )

        # Lấy ví người gửi
        sender_wallet = await self.repo.get_wallet_by_user_id(user_id)
        if sender_wallet is None:
            raise NotFoundException(
                message=f"Ví của user '{user_id}' không tồn tại",
                error_code="WALLET_NOT_FOUND",
            )

        # Tính phí
        fee = self.calculate_fee(tx_type, request.amount)
        utc_now = now_utc()
        transaction_id = f"txn_{generate_id()}"

        # Khởi tạo document giao dịch
        txn_doc = {
            "transaction_id": transaction_id,
            "user_id": user_id,
            "wallet_id": sender_wallet["wallet_id"],
            "amount": request.amount,
            "type": tx_type,
            "status": "PENDING",
            "fee": fee,
            "recipient_user_id": request.recipient_user_id,
            "recipient_wallet_id": None,
            "description": request.description,
            "idempotency_key": request.idempotency_key,
            "created_at": utc_now,
            "updated_at": utc_now,
        }

        try:
            if tx_type == "DEPOSIT":
                # DEPOSIT: cộng tiền vào ví
                new_balance = sender_wallet["balance"] + request.amount
                await self.repo.update_wallet_balance(sender_wallet["wallet_id"], new_balance, utc_now)

            elif tx_type == "WITHDRAWAL":
                # WITHDRAWAL: trừ tiền + phí khỏi ví
                total_debit = request.amount + fee
                if sender_wallet["balance"] < total_debit:
                    raise InsufficientBalanceException(
                        message=f"Số dư không đủ. Cần {total_debit:,} VND (gồm phí {fee:,}), hiện có {sender_wallet['balance']:,} VND",
                        details={
                            "required": total_debit,
                            "available": sender_wallet["balance"],
                            "fee": fee,
                        },
                    )
                new_balance = sender_wallet["balance"] - total_debit
                await self.repo.update_wallet_balance(sender_wallet["wallet_id"], new_balance, utc_now)

            elif tx_type == "TRANSFER":
                # TRANSFER: trừ ví gửi + cộng ví nhận
                total_debit = request.amount + fee

                # Kiểm tra số dư người gửi
                if sender_wallet["balance"] < total_debit:
                    raise InsufficientBalanceException(
                        message=f"Số dư không đủ để chuyển. Cần {total_debit:,} VND (gồm phí {fee:,}), hiện có {sender_wallet['balance']:,} VND",
                        details={
                            "required": total_debit,
                            "available": sender_wallet["balance"],
                            "fee": fee,
                        },
                    )

                # Lấy ví người nhận
                assert request.recipient_user_id is not None
                recipient_wallet = await self.repo.get_wallet_by_user_id(request.recipient_user_id)
                if recipient_wallet is None:
                    raise NotFoundException(
                        message=f"Ví của người nhận '{request.recipient_user_id}' không tồn tại",
                        error_code="RECIPIENT_WALLET_NOT_FOUND",
                    )

                txn_doc["recipient_wallet_id"] = recipient_wallet["wallet_id"]

                # Trừ ví người gửi
                sender_new_balance = sender_wallet["balance"] - total_debit
                await self.repo.update_wallet_balance(sender_wallet["wallet_id"], sender_new_balance, utc_now)

                # Cộng ví người nhận
                recipient_new_balance = recipient_wallet["balance"] + request.amount
                await self.repo.update_wallet_balance(recipient_wallet["wallet_id"], recipient_new_balance, utc_now)

            # Giao dịch thành công
            txn_doc["status"] = "SUCCESS"

        except (InsufficientBalanceException, NotFoundException):
            # Cho phép exception nghiệp vụ lan truyền lên, giao dịch không được tạo
            raise
        except Exception as e:
            # Lỗi kỹ thuật → đánh dấu FAILED
            txn_doc["status"] = "FAILED"
            logger.error(f"Transaction {transaction_id} failed: {e}")

        # Lưu giao dịch vào MongoDB
        await self.repo.create_transaction(txn_doc)
        logger.info(f"Transaction {transaction_id} ({tx_type}) → {txn_doc['status']}")

        return TransactionResponse(**txn_doc)

    async def get_transaction(self, transaction_id: str, current_user_id: str) -> TransactionResponse:
        """Lấy thông tin 1 giao dịch theo ID (yêu cầu phân quyền sở hữu)."""
        txn = await self.repo.get_transaction_by_id(transaction_id)
        if txn is None:
            raise NotFoundException(
                message=f"Giao dịch '{transaction_id}' không tồn tại",
                error_code="TRANSACTION_NOT_FOUND",
            )
        
        # Kiểm tra quyền sở hữu
        if txn.get("user_id") != current_user_id and txn.get("recipient_user_id") != current_user_id:
            raise ForbiddenException(
                message="Bạn không có quyền xem chi tiết giao dịch này",
                error_code="ACCESS_DENIED",
            )

        return TransactionResponse(**txn)

    async def get_transaction_history(
        self, user_id: str, limit: int = 20, skip: int = 0
    ) -> TransactionListResponse:
        """Lấy lịch sử giao dịch của user, sắp xếp mới nhất trước."""
        transactions = await self.repo.get_transactions_by_user_id(user_id, limit, skip)
        total = await self.repo.count_transactions_by_user_id(user_id)

        return TransactionListResponse(
            transactions=[TransactionResponse(**t) for t in transactions],
            total=total,
            limit=limit,
            skip=skip,
        )

    # ──────────────────── Fees ────────────────────

    @staticmethod
    def calculate_fee(transaction_type: str, amount: int) -> int:
        """
        Tính phí giao dịch.
        - WITHDRAWAL: 1,100 VND cố định
        - TRANSFER: 0 VND
        - DEPOSIT: 0 VND
        """
        return FEE_TABLE.get(transaction_type.upper(), 0)

    async def get_fee(self, transaction_type: str, amount: int) -> FeeResponse:
        """Tra cứu phí cho loại giao dịch và số tiền cụ thể."""
        tx_type = transaction_type.upper()
        if tx_type not in VALID_TRANSACTION_TYPES:
            raise BadRequestException(
                message=f"Loại giao dịch '{transaction_type}' không hợp lệ",
                error_code="INVALID_TRANSACTION_TYPE",
            )

        fee = self.calculate_fee(tx_type, amount)
        return FeeResponse(
            transaction_type=tx_type,
            amount=amount,
            fee=fee,
            currency="VND",
        )
