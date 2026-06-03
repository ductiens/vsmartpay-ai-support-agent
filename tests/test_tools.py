import pytest
from app.modules.tools.financial_tools import (
    check_balance,
    get_fee,
    get_transaction_status,
    get_user_kyc_status
)
from app.database import get_db

@pytest.mark.asyncio
async def test_check_balance():
    res = await check_balance("user_001")
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
    res = await get_transaction_status("txn_001", "user_001")
    assert res is not None
    assert res["transaction_id"] == "txn_001"
    assert res["status"] == "SUCCESS"
    assert res["amount"] == 100000

@pytest.mark.asyncio
async def test_get_user_kyc_status():
    status = await get_user_kyc_status("user_001")
    assert status == "VERIFIED"
