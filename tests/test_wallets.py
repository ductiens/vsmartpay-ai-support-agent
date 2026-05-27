"""Test wallets"""
import pytest
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.modules.users import service as users_service
from app.modules.users.schema import UserCreateRequest
from app.modules.wallets import service as wallets_service
from app.modules.wallets.schema import WalletCreateRequest
from app.common.exceptions import NotFoundException, BadRequestException
from app.common.constants import Currency, WalletStatus

pytestmark = pytest.mark.asyncio


# ==========================================
# SERVICE UNIT TESTS
# ==========================================

async def test_service_create_wallet_success(test_db: AsyncIOMotorDatabase):
    """Test creating a wallet successfully via service."""
    # 1. Create a user first
    user_req = UserCreateRequest(
        email="wallet_test@example.com",
        password="MySecretPassword123",
        full_name="Wallet Owner"
    )
    user = await users_service.create_user(test_db, user_req)
    
    # 2. Create wallet
    req = WalletCreateRequest(
        user_id=user["id"],
        currency=Currency.VND
    )
    wallet = await wallets_service.create_wallet(test_db, req)
    
    assert wallet["id"] is not None
    assert wallet["user_id"] == user["id"]
    assert wallet["currency"] == Currency.VND
    assert wallet["balance"] == 0
    assert wallet["status"] == WalletStatus.ACTIVE.value


async def test_service_create_wallet_user_not_found(test_db: AsyncIOMotorDatabase):
    """Test that creating a wallet for a non-existent user raises NotFoundException."""
    req = WalletCreateRequest(
        user_id="nonexistent-user-12345",
        currency=Currency.USD
    )
    
    with pytest.raises(NotFoundException) as excinfo:
        await wallets_service.create_wallet(test_db, req)
    assert excinfo.value.status_code == 404


# ==========================================
# ROUTER INTEGRATION & API TESTS
# ==========================================

async def test_api_create_wallet_success(client: AsyncClient):
    """POST /wallets - Success case"""
    # 1. Create user
    user_payload = {
        "email": "api_wallet@example.com",
        "password": "Password123",
        "full_name": "API Wallet User"
    }
    user_res = await client.post("/users", json=user_payload)
    assert user_res.status_code == 201
    user_id = user_res.json()["data"]["id"]
    
    # 2. Create wallet
    wallet_payload = {
        "user_id": user_id,
        "currency": "VND"
    }
    wallet_res = await client.post("/wallets", json=wallet_payload)
    assert wallet_res.status_code == 201
    
    body = wallet_res.json()
    assert body["success"] is True
    assert body["message"] == "Wallet created successfully"
    
    wallet_data = body["data"]
    assert wallet_data["id"] is not None
    assert wallet_data["user_id"] == user_id
    assert wallet_data["currency"] == "VND"
    assert wallet_data["balance"] == 0
    assert wallet_data["status"] == "ACTIVE"


async def test_api_create_wallet_user_not_found(client: AsyncClient):
    """POST /wallets - Fails if user does not exist"""
    wallet_payload = {
        "user_id": "nonexistent-user-99999",
        "currency": "USD"
    }
    wallet_res = await client.post("/wallets", json=wallet_payload)
    assert wallet_res.status_code == 404
    
    body = wallet_res.json()
    assert body["success"] is False
    assert body["error_code"] == "RESOURCE_NOT_FOUND"


async def test_api_create_wallet_invalid_currency(client: AsyncClient):
    """POST /wallets - Fails with invalid currency type"""
    # 1. Create user
    user_payload = {
        "email": "invalid_curr@example.com",
        "password": "Password123",
        "full_name": "Currency Tester"
    }
    user_res = await client.post("/users", json=user_payload)
    assert user_res.status_code == 201
    user_id = user_res.json()["data"]["id"]
    
    # 2. Create wallet with bad currency
    wallet_payload = {
        "user_id": user_id,
        "currency": "EUR"
    }
    wallet_res = await client.post("/wallets", json=wallet_payload)
    # Pydantic validation handles this, standard code 422 for Validation Error
    assert wallet_res.status_code == 422
    assert wallet_res.json()["success"] is False
    assert wallet_res.json()["error_code"] == "VALIDATION_ERROR"


async def test_api_get_wallet_by_id(client: AsyncClient):
    """GET /wallets/{wallet_id} - Success & Not Found cases"""
    # 1. Create user and wallet
    user_payload = {
        "email": "fetch_wallet@example.com",
        "password": "Password123",
        "full_name": "Wallet Fetcher"
    }
    user_res = await client.post("/users", json=user_payload)
    user_id = user_res.json()["data"]["id"]
    
    wallet_res = await client.post("/wallets", json={"user_id": user_id, "currency": "USD"})
    wallet_id = wallet_res.json()["data"]["id"]
    
    # 2. Fetch wallet details
    get_res = await client.get(f"/wallets/{wallet_id}")
    assert get_res.status_code == 200
    
    body = get_res.json()
    assert body["success"] is True
    assert body["data"]["id"] == wallet_id
    assert body["data"]["currency"] == "USD"
    assert body["data"]["balance"] == 0
    
    # 3. Fetch non-existent wallet
    get_fail = await client.get("/wallets/invalid-wallet-id")
    assert get_fail.status_code == 404
    assert get_fail.json()["success"] is False


async def test_api_list_user_wallets(client: AsyncClient):
    """GET /users/{user_id}/wallets - List multiple wallets"""
    # 1. Create user
    user_payload = {
        "email": "multi_wallets@example.com",
        "password": "Password123",
        "full_name": "Multi Wallet User"
    }
    user_res = await client.post("/users", json=user_payload)
    user_id = user_res.json()["data"]["id"]
    
    # 2. Create multiple wallets
    await client.post("/wallets", json={"user_id": user_id, "currency": "VND"})
    await client.post("/wallets", json={"user_id": user_id, "currency": "USD"})
    
    # 3. List wallets
    list_res = await client.get(f"/users/{user_id}/wallets")
    assert list_res.status_code == 200
    
    body = list_res.json()
    assert body["success"] is True
    
    wallets_list = body["data"]
    assert len(wallets_list) == 2
    
    currencies = [w["currency"] for w in wallets_list]
    assert "VND" in currencies
    assert "USD" in currencies
    
    # 4. List wallets for non-existent user
    list_fail = await client.get("/users/nonexistent-user-id/wallets")
    assert list_fail.status_code == 404
