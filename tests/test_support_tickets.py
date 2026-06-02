import pytest
from httpx import AsyncClient
from app.config import settings
from app.database import get_db

API_PREFIX = settings.API_V1_STR  # /api/v1

async def register_and_login(client: AsyncClient, suffix: str):
    """
    Helper to register a user and log in to get a JWT access token.
    Returns (user_data, headers).
    """
    phone = f"09111111{ord(suffix) % 100:02d}"
    
    # 1. Register User
    user_resp = await client.post(f"{API_PREFIX}/finance/users", json={
        "full_name": f"Support User {suffix}",
        "phone": phone,
        "email": f"support_{suffix.lower()}@example.com",
        "password": "password123",
    })
    assert user_resp.status_code == 201
    user_data = user_resp.json()["data"]

    # 2. Login
    login_resp = await client.post(f"{API_PREFIX}/finance/login", json={
        "phone": phone,
        "password": "password123",
    })
    assert login_resp.status_code == 200
    token_data = login_resp.json()["data"]
    access_token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    return user_data, headers

@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient):
    """Endpoints require valid authentication and fail with 401 on missing/invalid token."""
    bad_headers = {"Authorization": "Bearer bad_token_here"}
    
    # 1. POST /support/tickets
    resp = await client.post(f"{API_PREFIX}/support/tickets", json={
        "session_id": "sess_123",
        "priority": "HIGH",
        "summary": "Need help"
    }, headers=bad_headers)
    assert resp.status_code == 401
    
    # 2. GET /support/tickets
    resp = await client.get(f"{API_PREFIX}/support/tickets", headers=bad_headers)
    assert resp.status_code == 401
    
    # 3. GET /support/tickets/{ticket_id}
    resp = await client.get(f"{API_PREFIX}/support/tickets/any_tkt_id", headers=bad_headers)
    assert resp.status_code == 401

@pytest.mark.asyncio
async def test_create_and_list_tickets(client: AsyncClient):
    """Verifies manual support ticket creation, listing and detail views for authorized users."""
    user, headers = await register_and_login(client, "A")
    session_id = "sess_manual_01"
    
    # 1. Create support ticket
    create_resp = await client.post(f"{API_PREFIX}/support/tickets", json={
        "session_id": session_id,
        "priority": "HIGH",
        "summary": "Tôi gặp lỗi không nạp được tiền vào ví."
    }, headers=headers)
    
    assert create_resp.status_code == 201
    data = create_resp.json()["data"]
    assert "ticket_id" in data
    assert data["session_id"] == session_id
    assert data["user_id"] == user["user_id"]
    assert data["priority"] == "HIGH"
    assert data["status"] == "OPEN"
    assert data["summary"] == "Tôi gặp lỗi không nạp được tiền vào ví."
    assert data["assigned_agent_id"] is None
    
    ticket_id = data["ticket_id"]
    
    # 2. List user tickets
    list_resp = await client.get(f"{API_PREFIX}/support/tickets", headers=headers)
    assert list_resp.status_code == 200
    tickets = list_resp.json()["data"]
    assert len(tickets) > 0
    assert tickets[0]["ticket_id"] == ticket_id
    assert tickets[0]["session_id"] == session_id
    assert tickets[0]["user_id"] == user["user_id"]
    
    # 3. Get ticket detail
    detail_resp = await client.get(f"{API_PREFIX}/support/tickets/{ticket_id}", headers=headers)
    assert detail_resp.status_code == 200
    detail = detail_resp.json()["data"]
    assert detail["ticket_id"] == ticket_id
    assert detail["summary"] == "Tôi gặp lỗi không nạp được tiền vào ví."

@pytest.mark.asyncio
async def test_ticket_ownership_authorization(client: AsyncClient):
    """Verifies that a user cannot access another user's support ticket (403 Forbidden)."""
    user_a, headers_a = await register_and_login(client, "A")
    _, headers_b = await register_and_login(client, "B")
    
    # User A creates a ticket
    create_resp = await client.post(f"{API_PREFIX}/support/tickets", json={
        "session_id": "sess_a_01",
        "priority": "LOW",
        "summary": "Lỗi hiển thị giao diện ví"
    }, headers=headers_a)
    assert create_resp.status_code == 201
    ticket_id = create_resp.json()["data"]["ticket_id"]
    
    # User B tries to retrieve User A's ticket -> 403 Forbidden
    resp = await client.get(f"{API_PREFIX}/support/tickets/{ticket_id}", headers=headers_b)
    assert resp.status_code == 403
    assert resp.json()["message"] == "Bạn không có quyền truy cập ticket hỗ trợ này."

@pytest.mark.asyncio
async def test_automatic_chat_escalation_linkage(client: AsyncClient):
    """
    Verifies that when a chat message triggers automatic escalation,
    the support ticket generated in the DB is correctly linked to the chat session.
    """
    user, headers = await register_and_login(client, "A")
    session_id = f"sess_auto_esc_{user['user_id']}"
    
    # Send a message triggering escalation (critical fraud/security report)
    chat_resp = await client.post("/chat", json={
        "session_id": session_id,
        "message": "Tôi bị lộ otp và bị hack tài khoản ví VSmartPay, hãy khoá tài khoản khẩn cấp!"
    }, headers=headers)
    
    assert chat_resp.status_code == 200
    chat_data = chat_resp.json()
    assert chat_data["escalation"]["required"] is True
    
    # Verify support ticket was automatically generated in MongoDB
    db = get_db()
    assert db is not None
    
    ticket = await db["support_tickets"].find_one({"session_id": session_id})
    assert ticket is not None
    assert ticket["user_id"] == user["user_id"]
    assert ticket["priority"] in ["HIGH", "CRITICAL"]
    assert "tkt_" in ticket["ticket_id"]
    assert ticket["status"] == "OPEN"
    assert "lộ otp" in ticket["summary"] or "bị hack" in ticket["summary"]
