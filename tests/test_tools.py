import pytest
from app.modules.tools.mock_wallet import (
    check_balance,
    get_fee,
    get_transaction_status,
    get_user_kyc_status,
    create_support_ticket
)
from app.database import get_db

@pytest.mark.asyncio
async def test_check_balance():
    res = check_balance("user_001")
    assert res is not None
    assert res["user_id"] == "user_001"
    assert res["balance"] == 2500000
    assert res["currency"] == "VND"

@pytest.mark.asyncio
async def test_get_fee_transfer():
    res = get_fee("TRANSFER", 500000)
    assert res["transaction_type"] == "TRANSFER"
    assert res["fee"] == 0

@pytest.mark.asyncio
async def test_get_fee_withdrawal():
    res = get_fee("WITHDRAWAL", 200000)
    assert res["transaction_type"] == "WITHDRAWAL"
    assert res["fee"] == 1100

@pytest.mark.asyncio
async def test_get_transaction_status():
    res = get_transaction_status("txn_001")
    assert res is not None
    assert res["transaction_id"] == "txn_001"
    assert res["status"] == "SUCCESS"
    assert res["amount"] == 100000

@pytest.mark.asyncio
async def test_get_user_kyc_status():
    status = get_user_kyc_status("user_001")
    assert status == "VERIFIED"

@pytest.mark.asyncio
async def test_create_support_ticket():
    res = await create_support_ticket(
        user_id="user_test_ticket",
        issue_type="FRAUD",
        message="Báo cáo lừa đảo gấp!"
    )
    assert res["user_id"] == "user_test_ticket"
    assert res["issue_type"] == "FRAUD"
    assert "ticket_id" in res
    assert res["status"] == "OPEN"
    
    # Verify it was inserted in database
    db = get_db()
    inserted = await db["escalation_tickets"].find_one({"ticket_id": res["ticket_id"]})
    assert inserted is not None
    assert inserted["user_id"] == "user_test_ticket"
