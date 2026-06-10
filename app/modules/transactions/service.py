import logging
from app.common.utils import generate_id, now_utc
from app.common.exceptions import BadRequestException, DuplicateRequestException, InsufficientBalanceException, NotFoundException, ForbiddenException
from app.modules.transactions.repository import TransactionsRepository
from app.modules.transactions.schema import CreateTransactionRequest, TransactionResponse, TransactionListResponse
from app.modules.wallets.repository import WalletsRepository
from app.modules.fees.service import FeesService, VALID_TRANSACTION_TYPES

logger = logging.getLogger(__name__)

class TransactionsService:
    def __init__(self) -> None:
        self.repo = TransactionsRepository()
        self.wallets_repo = WalletsRepository()
        self.fees_svc = FeesService()

    async def create_transaction(self, request: CreateTransactionRequest, user_id: str) -> TransactionResponse:
        tx_type = request.type.value
        if tx_type not in VALID_TRANSACTION_TYPES:
            raise BadRequestException(
                message=f"Loại giao dịch '{request.type}' không hợp lệ. Chấp nhận: {', '.join(VALID_TRANSACTION_TYPES)}",
                error_code="INVALID_TRANSACTION_TYPE",
            )
        if tx_type == "TRANSFER" and not request.recipient_user_id:
            raise BadRequestException(
                message="Giao dịch TRANSFER yêu cầu trường 'recipient_user_id'",
                error_code="MISSING_RECIPIENT",
            )
        if tx_type == "TRANSFER" and request.recipient_user_id == user_id:
            raise BadRequestException(
                message="Không thể chuyển tiền cho chính mình",
                error_code="SELF_TRANSFER",
            )
        if request.idempotency_key:
            existing_txn = await self.repo.get_transaction_by_idempotency_key(request.idempotency_key)
            if existing_txn is not None:
                raise DuplicateRequestException(
                    message=f"Giao dịch với idempotency_key '{request.idempotency_key}' đã tồn tại",
                    error_code="DUPLICATE_TRANSACTION",
                    details={"existing_transaction_id": existing_txn["transaction_id"]},
                )

        sender_wallet = await self.wallets_repo.get_wallet_by_user_id(user_id)
        if sender_wallet is None:
            raise NotFoundException(
                message=f"Ví của user '{user_id}' không tồn tại",
                error_code="WALLET_NOT_FOUND",
            )

        fee = self.fees_svc.calculate_fee(tx_type, request.amount)
        utc_now = now_utc()
        transaction_id = f"txn_{generate_id()}"

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
                new_balance = sender_wallet["balance"] + request.amount
                await self.wallets_repo.update_wallet_balance(sender_wallet["wallet_id"], new_balance, utc_now)
            elif tx_type == "WITHDRAWAL":
                total_debit = request.amount + fee
                if sender_wallet["balance"] < total_debit:
                    raise InsufficientBalanceException(
                        message=f"Số dư không đủ. Cần {total_debit:,} VND (gồm phí {fee:,}), hiện có {sender_wallet['balance']:,} VND",
                        details={"required": total_debit, "available": sender_wallet["balance"], "fee": fee},
                    )
                new_balance = sender_wallet["balance"] - total_debit
                await self.wallets_repo.update_wallet_balance(sender_wallet["wallet_id"], new_balance, utc_now)
            elif tx_type == "TRANSFER":
                total_debit = request.amount + fee
                if sender_wallet["balance"] < total_debit:
                    raise InsufficientBalanceException(
                        message=f"Số dư không đủ để chuyển. Cần {total_debit:,} VND (gồm phí {fee:,}), hiện có {sender_wallet['balance']:,} VND",
                        details={"required": total_debit, "available": sender_wallet["balance"], "fee": fee},
                    )
                assert request.recipient_user_id is not None
                recipient_wallet = await self.wallets_repo.get_wallet_by_user_id(request.recipient_user_id)
                if recipient_wallet is None:
                    raise NotFoundException(
                        message=f"Ví của người nhận '{request.recipient_user_id}' không tồn tại",
                        error_code="RECIPIENT_WALLET_NOT_FOUND",
                    )
                txn_doc["recipient_wallet_id"] = recipient_wallet["wallet_id"]
                sender_new_balance = sender_wallet["balance"] - total_debit
                await self.wallets_repo.update_wallet_balance(sender_wallet["wallet_id"], sender_new_balance, utc_now)
                recipient_new_balance = recipient_wallet["balance"] + request.amount
                await self.wallets_repo.update_wallet_balance(recipient_wallet["wallet_id"], recipient_new_balance, utc_now)
            txn_doc["status"] = "SUCCESS"
        except (InsufficientBalanceException, NotFoundException):
            raise
        except Exception as e:
            txn_doc["status"] = "FAILED"
            logger.error(f"Transaction {transaction_id} failed: {e}")

        await self.repo.create_transaction(txn_doc)
        logger.info(f"Transaction {transaction_id} ({tx_type}) → {txn_doc['status']}")
        return TransactionResponse(**txn_doc)

    async def get_transaction(self, transaction_id: str, current_user_id: str) -> TransactionResponse:
        txn = await self.repo.get_transaction_by_id(transaction_id)
        if txn is None:
            raise NotFoundException(
                message=f"Giao dịch '{transaction_id}' không tồn tại",
                error_code="TRANSACTION_NOT_FOUND",
            )
        if txn.get("user_id") != current_user_id and txn.get("recipient_user_id") != current_user_id:
            raise ForbiddenException(
                message="Bạn không có quyền xem chi tiết giao dịch này",
                error_code="ACCESS_DENIED",
            )
        return TransactionResponse(**txn)

    async def get_transaction_history(self, user_id: str, limit: int = 20, skip: int = 0) -> TransactionListResponse:
        transactions = await self.repo.get_transactions_by_user_id(user_id, limit, skip)
        total = await self.repo.count_transactions_by_user_id(user_id)
        return TransactionListResponse(
            transactions=[TransactionResponse(**t) for t in transactions],
            total=total,
            limit=limit,
            skip=skip,
        )
