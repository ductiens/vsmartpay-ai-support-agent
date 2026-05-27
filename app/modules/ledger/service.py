"""Ledger service"""
from typing import List, Tuple, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.modules.ledger import repository
from app.modules.wallets import service as wallets_service
from app.modules.wallets import repository as wallets_repository
from app.common.exceptions import BadRequestException, InsufficientBalanceException, NotFoundException
from app.common.constants import LedgerEntryType, Currency

def validate_double_entry(debit_entries: List[dict], credit_entries: List[dict]) -> bool:
    """
    Ensure the sum of debits equals the sum of credits for a double-entry ledger transaction.
    """
    total_debit = sum(entry["amount"] for entry in debit_entries)
    total_credit = sum(entry["amount"] for entry in credit_entries)
    
    if total_debit != total_credit:
        raise BadRequestException(
            message=f"Double-entry validation failed: Total DEBIT ({total_debit}) must equal Total CREDIT ({total_credit}).",
            error_code="LEDGER_UNBALANCED"
        )
    return True


async def create_debit_entry(
    db: AsyncIOMotorDatabase,
    transaction_id: str,
    wallet_id: str,
    amount: int,
    currency: Currency,
    description: Optional[str] = None
) -> dict:
    """
    Create a DEBIT entry (decreases wallet balance):
    - Verify wallet exists and is active.
    - Verify currency matches.
    - Check if wallet has sufficient balance.
    - Update wallet balance and write ledger entry.
    """
    if amount <= 0:
        raise BadRequestException(
            message="Amount must be greater than zero.",
            error_code="INVALID_AMOUNT"
        )
        
    # 1. Fetch wallet
    wallet = await wallets_service.get_wallet_by_id(db, wallet_id)
    
    # 2. Verify currency
    if wallet["currency"] != currency:
        raise BadRequestException(
            message=f"Wallet {wallet_id} currency '{wallet['currency']}' does not match entry currency '{currency}'.",
            error_code="CURRENCY_MISMATCH"
        )
        
    # 3. Check balance
    if wallet["balance"] < amount:
        raise InsufficientBalanceException(
            message=f"Wallet {wallet_id} has insufficient balance. Required: {amount}, Available: {wallet['balance']}.",
            error_code="INSUFFICIENT_BALANCE"
        )
        
    # 4. Update wallet balance
    new_balance = wallet["balance"] - amount
    await wallets_repository.update_wallet_balance(db, wallet_id, new_balance)
    
    # 5. Write ledger entry
    entry_data = {
        "transaction_id": transaction_id,
        "wallet_id": wallet_id,
        "entry_type": LedgerEntryType.DEBIT.value,
        "amount": amount,
        "currency": currency,
        "description": description
    }
    return await repository.create_ledger_entry(db, entry_data)


async def create_credit_entry(
    db: AsyncIOMotorDatabase,
    transaction_id: str,
    wallet_id: str,
    amount: int,
    currency: Currency,
    description: Optional[str] = None
) -> dict:
    """
    Create a CREDIT entry (increases wallet balance):
    - Verify wallet exists and is active.
    - Verify currency matches.
    - Update wallet balance and write ledger entry.
    """
    if amount <= 0:
        raise BadRequestException(
            message="Amount must be greater than zero.",
            error_code="INVALID_AMOUNT"
        )
        
    # 1. Fetch wallet
    wallet = await wallets_service.get_wallet_by_id(db, wallet_id)
    
    # 2. Verify currency
    if wallet["currency"] != currency:
        raise BadRequestException(
            message=f"Wallet {wallet_id} currency '{wallet['currency']}' does not match entry currency '{currency}'.",
            error_code="CURRENCY_MISMATCH"
        )
        
    # 3. Update wallet balance
    new_balance = wallet["balance"] + amount
    await wallets_repository.update_wallet_balance(db, wallet_id, new_balance)
    
    # 4. Write ledger entry
    entry_data = {
        "transaction_id": transaction_id,
        "wallet_id": wallet_id,
        "entry_type": LedgerEntryType.CREDIT.value,
        "amount": amount,
        "currency": currency,
        "description": description
    }
    return await repository.create_ledger_entry(db, entry_data)


async def record_double_entry_transaction(
    db: AsyncIOMotorDatabase,
    transaction_id: str,
    debit_wallet_id: str,
    credit_wallet_id: str,
    amount: int,
    currency: Currency,
    description: Optional[str] = None
) -> Tuple[dict, dict]:
    """
    Record a balanced transfer transaction:
    - 1 DEBIT entry (sender)
    - 1 CREDIT entry (receiver)
    - Reverts the debit balance if the credit entry fails.
    """
    # 1. Record Debit (deducts from sender)
    debit_entry = await create_debit_entry(db, transaction_id, debit_wallet_id, amount, currency, description)
    
    try:
        # 2. Record Credit (adds to receiver)
        credit_entry = await create_credit_entry(db, transaction_id, credit_wallet_id, amount, currency, description)
    except Exception as e:
        # Revert Debit if Credit fails to ensure double-entry integrity
        sender_wallet = await wallets_service.get_wallet_by_id(db, debit_wallet_id)
        reverted_balance = sender_wallet["balance"] + amount
        await wallets_repository.update_wallet_balance(db, debit_wallet_id, reverted_balance)
        raise e
        
    # 3. Double-entry validation
    validate_double_entry([debit_entry], [credit_entry])
    
    return debit_entry, credit_entry


async def get_entries_by_wallet_id(db: AsyncIOMotorDatabase, wallet_id: str) -> List[dict]:
    """
    Retrieve all ledger entries of a wallet, raising NotFoundException if wallet does not exist.
    """
    # Check if wallet exists
    await wallets_service.get_wallet_by_id(db, wallet_id)
    return await repository.get_entries_by_wallet_id(db, wallet_id)


async def get_entries_by_transaction_id(db: AsyncIOMotorDatabase, transaction_id: str) -> List[dict]:
    """
    Retrieve all ledger entries of a transaction.
    """
    return await repository.get_entries_by_transaction_id(db, transaction_id)
