"""Test ledger"""
import pytest
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.modules.users import service as users_service
from app.modules.users.schema import UserCreateRequest
from app.modules.wallets import service as wallets_service
from app.modules.wallets import repository as wallets_repository
from app.modules.wallets.schema import WalletCreateRequest
from app.modules.ledger import service as ledger_service
from app.common.exceptions import BadRequestException, InsufficientBalanceException
from app.common.constants import Currency, LedgerEntryType

pytestmark = pytest.mark.asyncio


async def _setup_test_user_and_wallet(db: AsyncIOMotorDatabase, email: str, currency: Currency, initial_balance: int = 0) -> dict:
    """Helper to set up a user and active wallet with a specific balance."""
    user_req = UserCreateRequest(
        email=email,
        password="Password123",
        full_name="Ledger Tester"
    )
    user = await users_service.create_user(db, user_req)
    
    wallet_req = WalletCreateRequest(
        user_id=user["id"],
        currency=currency
    )
    wallet = await wallets_service.create_wallet(db, wallet_req)
    
    if initial_balance > 0:
        await wallets_repository.update_wallet_balance(db, wallet["id"], initial_balance)
        wallet["balance"] = initial_balance
        
    return wallet


# ==========================================
# SERVICE UNIT TESTS
# ==========================================

async def test_validate_double_entry():
    """Test validation of debit and credit amounts."""
    # Balanced
    debits = [{"amount": 100}, {"amount": 200}]
    credits = [{"amount": 150}, {"amount": 150}]
    assert ledger_service.validate_double_entry(debits, credits) is True
    
    # Unbalanced
    debits = [{"amount": 100}]
    credits = [{"amount": 150}]
    with pytest.raises(BadRequestException) as excinfo:
        ledger_service.validate_double_entry(debits, credits)
    assert excinfo.value.error_code == "LEDGER_UNBALANCED"


async def test_record_double_entry_transaction_success(test_db: AsyncIOMotorDatabase):
    """Test a successful transfer hach toan ledger."""
    # 1. Setup Wallet A (100,000 VND) & Wallet B (0 VND)
    wallet_a = await _setup_test_user_and_wallet(test_db, "sender@example.com", Currency.VND, 100000)
    wallet_b = await _setup_test_user_and_wallet(test_db, "receiver@example.com", Currency.VND, 0)
    
    tx_id = "test-transaction-12345"
    
    # 2. Record double-entry transfer of 40,000 VND
    debit, credit = await ledger_service.record_double_entry_transaction(
        test_db,
        transaction_id=tx_id,
        debit_wallet_id=wallet_a["id"],
        credit_wallet_id=wallet_b["id"],
        amount=40000,
        currency=Currency.VND,
        description="P2P Transfer 40k VND"
    )
    
    # 3. Assert debit details
    assert debit["id"] is not None
    assert debit["transaction_id"] == tx_id
    assert debit["wallet_id"] == wallet_a["id"]
    assert debit["entry_type"] == LedgerEntryType.DEBIT.value
    assert debit["amount"] == 40000
    assert debit["currency"] == Currency.VND
    
    # 4. Assert credit details
    assert credit["id"] is not None
    assert credit["transaction_id"] == tx_id
    assert credit["wallet_id"] == wallet_b["id"]
    assert credit["entry_type"] == LedgerEntryType.CREDIT.value
    assert credit["amount"] == 40000
    assert credit["currency"] == Currency.VND
    
    # 5. Assert wallet balances were updated in the DB
    updated_a = await wallets_service.get_wallet_by_id(test_db, wallet_a["id"])
    updated_b = await wallets_service.get_wallet_by_id(test_db, wallet_b["id"])
    assert updated_a["balance"] == 60000
    assert updated_b["balance"] == 40000


async def test_record_double_entry_transaction_insufficient_balance(test_db: AsyncIOMotorDatabase):
    """Test transfer is rejected if sender has insufficient balance."""
    wallet_a = await _setup_test_user_and_wallet(test_db, "sender2@example.com", Currency.VND, 10000)
    wallet_b = await _setup_test_user_and_wallet(test_db, "receiver2@example.com", Currency.VND, 0)
    
    # Try to transfer 15,000 VND (sender has only 10,000 VND)
    with pytest.raises(InsufficientBalanceException) as excinfo:
        await ledger_service.record_double_entry_transaction(
            test_db,
            transaction_id="tx-insufficient-123",
            debit_wallet_id=wallet_a["id"],
            credit_wallet_id=wallet_b["id"],
            amount=15000,
            currency=Currency.VND
        )
    assert excinfo.value.error_code == "INSUFFICIENT_BALANCE"
    
    # Assert balances remain unchanged
    updated_a = await wallets_service.get_wallet_by_id(test_db, wallet_a["id"])
    updated_b = await wallets_service.get_wallet_by_id(test_db, wallet_b["id"])
    assert updated_a["balance"] == 10000
    assert updated_b["balance"] == 0


async def test_record_double_entry_transaction_currency_mismatch(test_db: AsyncIOMotorDatabase):
    """Test that currency mismatch between wallet and transaction is rejected."""
    wallet_a = await _setup_test_user_and_wallet(test_db, "sender3@example.com", Currency.VND, 50000)
    wallet_c = await _setup_test_user_and_wallet(test_db, "receiver3@example.com", Currency.USD, 0)
    
    # Try to send USD using wallet_a (VND)
    with pytest.raises(BadRequestException) as excinfo:
        await ledger_service.record_double_entry_transaction(
            test_db,
            transaction_id="tx-mismatch-123",
            debit_wallet_id=wallet_a["id"],
            credit_wallet_id=wallet_c["id"],
            amount=10,
            currency=Currency.USD
        )
    assert excinfo.value.error_code == "CURRENCY_MISMATCH"


# ==========================================
# ROUTER INTEGRATION & API TESTS
# ==========================================

async def test_api_ledger_queries(client: AsyncClient, test_db: AsyncIOMotorDatabase):
    """Test retrieving ledger entries by wallet ID and transaction ID."""
    # 1. Setup wallets via API (using repository update in test for mock balances)
    # Register sender
    res1 = await client.post("/users", json={"email": "sender_api@example.com", "password": "Password123", "full_name": "S"})
    uid1 = res1.json()["data"]["id"]
    wres1 = await client.post("/wallets", json={"user_id": uid1, "currency": "VND"})
    wid1 = wres1.json()["data"]["id"]
    
    # Register receiver
    res2 = await client.post("/users", json={"email": "receiver_api@example.com", "password": "Password123", "full_name": "R"})
    uid2 = res2.json()["data"]["id"]
    wres2 = await client.post("/wallets", json={"user_id": uid2, "currency": "VND"})
    wid2 = wres2.json()["data"]["id"]
    
    # Inject balance directly using test_db
    await wallets_repository.update_wallet_balance(test_db, wid1, 100000)
    
    # 2. Record ledger entries directly through service (simulate transaction completion)
    tx_id = "api-tx-id-999"
    await ledger_service.record_double_entry_transaction(
        test_db,
        transaction_id=tx_id,
        debit_wallet_id=wid1,
        credit_wallet_id=wid2,
        amount=30000,
        currency=Currency.VND,
        description="P2P 30k"
    )
    
    # 3. GET /ledger/wallets/{wallet_id} for sender
    get_wallet_res = await client.get(f"/ledger/wallets/{wid1}")
    assert get_wallet_res.status_code == 200
    body = get_wallet_res.json()
    assert body["success"] is True
    assert len(body["data"]) == 1
    assert body["data"][0]["wallet_id"] == wid1
    assert body["data"][0]["entry_type"] == "DEBIT"
    assert body["data"][0]["amount"] == 30000
    
    # 4. GET /ledger/transactions/{transaction_id}
    get_tx_res = await client.get(f"/ledger/transactions/{tx_id}")
    assert get_tx_res.status_code == 200
    tx_body = get_tx_res.json()
    assert tx_body["success"] is True
    assert len(tx_body["data"]) == 2
    
    entries = tx_body["data"]
    wallet_ids = [e["wallet_id"] for e in entries]
    assert wid1 in wallet_ids
    assert wid2 in wallet_ids
    
    types = [e["entry_type"] for e in entries]
    assert "DEBIT" in types
    assert "CREDIT" in types
