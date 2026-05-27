"""Test users"""
import pytest
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.modules.users import service, repository
from app.modules.users.schema import UserCreateRequest
from app.common.exceptions import BadRequestException, NotFoundException
from app.common.utils import verify_password

pytestmark = pytest.mark.asyncio


# ==========================================
# REPOSITORY & SERVICE UNIT TESTS
# ==========================================

async def test_repository_create_and_get_user(test_db: AsyncIOMotorDatabase):
    """Test user creation and retrieval directly via repository."""
    user_data = {
        "email": "repo_test@example.com",
        "password_hash": "somehashedpassword123",
        "full_name": "Repo Tester"
    }
    
    # 1. Create
    created_user = await repository.create_user(test_db, user_data)
    assert created_user["_id"] is not None
    assert created_user["email"] == "repo_test@example.com"
    assert created_user["full_name"] == "Repo Tester"
    assert created_user["password_hash"] == "somehashedpassword123"
    assert created_user["id"] == created_user["_id"]
    
    # 2. Get by ID
    fetched_by_id = await repository.get_user_by_id(test_db, created_user["id"])
    assert fetched_by_id is not None
    assert fetched_by_id["email"] == "repo_test@example.com"
    
    # 3. Get by Email (case-insensitive and trimmed)
    fetched_by_email = await repository.get_user_by_email(test_db, " REPO_TEST@example.com ")
    assert fetched_by_email is not None
    assert fetched_by_email["id"] == created_user["id"]


async def test_service_create_user(test_db: AsyncIOMotorDatabase):
    """Test user creation, including password hashing, via service."""
    req = UserCreateRequest(
        email="service_test@example.com",
        password="MySecretPassword123",
        full_name="Service Tester"
    )
    
    # Create user
    user = await service.create_user(test_db, req)
    assert user["id"] is not None
    assert user["email"] == "service_test@example.com"
    assert user["full_name"] == "Service Tester"
    
    # Verify password was hashed and is verify-able
    assert user["password_hash"] is not None
    assert user["password_hash"] != "MySecretPassword123"
    assert verify_password("MySecretPassword123", user["password_hash"]) is True
    
    # Try creating again with duplicate email (should raise BadRequestException)
    with pytest.raises(BadRequestException) as excinfo:
        await service.create_user(test_db, req)
    assert excinfo.value.error_code == "EMAIL_ALREADY_EXISTS"
    assert "Email already registered" in excinfo.value.message


async def test_service_get_user_not_found(test_db: AsyncIOMotorDatabase):
    """Test get_user_by_id throws NotFoundException when user does not exist."""
    with pytest.raises(NotFoundException) as excinfo:
        await service.get_user_by_id(test_db, "nonexistent-id-12345")
    assert excinfo.value.status_code == 404
    assert excinfo.value.error_code == "RESOURCE_NOT_FOUND"


# ==========================================
# ROUTER INTEGRATION & API TESTS
# ==========================================

async def test_api_create_user_success(client: AsyncClient):
    """POST /users - Success case"""
    payload = {
        "email": "api_test@example.com",
        "password": "SecurePassword123",
        "full_name": "API Tester"
    }
    
    response = await client.post("/users", json=payload)
    assert response.status_code == 201
    
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "User created successfully"
    
    user_data = body["data"]
    assert user_data["id"] is not None
    assert user_data["email"] == "api_test@example.com"
    assert user_data["full_name"] == "API Tester"
    # Ensure sensitive password hash info is NOT returned in the schema
    assert "password" not in user_data
    assert "password_hash" not in user_data


async def test_api_create_user_duplicate_email(client: AsyncClient):
    """POST /users - Rejects duplicate emails"""
    payload = {
        "email": "dup_test@example.com",
        "password": "Password123",
        "full_name": "First User"
    }
    
    # 1. Create first user
    res1 = await client.post("/users", json=payload)
    assert res1.status_code == 201
    
    # 2. Try creating second user with duplicate email
    res2 = await client.post("/users", json=payload)
    assert res2.status_code == 400
    
    body = res2.json()
    assert body["success"] is False
    assert body["error_code"] == "EMAIL_ALREADY_EXISTS"
    assert "Email already registered" in body["message"]


async def test_api_get_user_by_id(client: AsyncClient):
    """GET /users/{user_id} - Success & Not Found cases"""
    # 1. Create a user
    payload = {
        "email": "fetch_test@example.com",
        "password": "Password123",
        "full_name": "Fetch Tester"
    }
    create_res = await client.post("/users", json=payload)
    user_id = create_res.json()["data"]["id"]
    
    # 2. Get existing user
    get_res = await client.get(f"/users/{user_id}")
    assert get_res.status_code == 200
    body = get_res.json()
    assert body["success"] is True
    assert body["data"]["id"] == user_id
    assert body["data"]["email"] == "fetch_test@example.com"
    assert body["data"]["full_name"] == "Fetch Tester"
    
    # 3. Get non-existent user
    get_fail_res = await client.get("/users/invalid-id-99999")
    assert get_fail_res.status_code == 404
    assert get_fail_res.json()["success"] is False
    assert get_fail_res.json()["error_code"] == "RESOURCE_NOT_FOUND"


async def test_api_list_users(client: AsyncClient):
    """GET /users - Success and pagination checks"""
    # Create two users
    u1 = {"email": "user1@example.com", "password": "Password1", "full_name": "User One"}
    u2 = {"email": "user2@example.com", "password": "Password2", "full_name": "User Two"}
    
    await client.post("/users", json=u1)
    await client.post("/users", json=u2)
    
    # Get all users
    list_res = await client.get("/users")
    assert list_res.status_code == 200
    
    body = list_res.json()
    assert body["success"] is True
    users_list = body["data"]
    # We should have at least 2 users in the DB
    assert len(users_list) >= 2
    
    emails = [u["email"] for u in users_list]
    assert "user1@example.com" in emails
    assert "user2@example.com" in emails
    
    # Test pagination (limit=1)
    limit_res = await client.get("/users?limit=1")
    assert limit_res.status_code == 200
    assert len(limit_res.json()["data"]) == 1
