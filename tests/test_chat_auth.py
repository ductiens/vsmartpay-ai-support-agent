"""
Integration tests for JWT Authentication and ownership authorization in the Chat module.
Verifies secure message processing, session listing, and message history controls.
"""
import pytest
from httpx import AsyncClient
from app.config import settings

API_PREFIX = settings.API_V1_STR  # /api/v1


# ──────────────────── Helper to seed user ────────────────────

async def register_and_login(client: AsyncClient, suffix: str):
    """
    Helper to register a user and log in to get a JWT access token.
    Returns (user_data, headers).
    """
    phone = f"09999999{ord(suffix) % 100:02d}"
    
    # 1. Register User
    user_resp = await client.post(f"{API_PREFIX}/users", json={
        "full_name": f"Chat User {suffix}",
        "phone": phone,
        "email": f"chat_{suffix.lower()}@example.com",
        "password": "password123",
    })
    assert user_resp.status_code == 201
    user_data = user_resp.json()["data"]

    # 2. Login
    login_resp = await client.post(f"{API_PREFIX}/login", json={
        "phone": phone,
        "password": "password123",
    })
    assert login_resp.status_code == 200
    token_data = login_resp.json()["data"]
    access_token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    return user_data, headers


# ══════════════════════════════════════════════════════════════
# TESTS
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_chat_endpoints_unauthorized(client):
    """Endpoints require valid authentication and fail with 401 on invalid token."""
    bad_headers = {"Authorization": "Bearer bad_token_here"}
    
    # 1. POST /chat
    resp = await client.post("/chat", json={
        "session_id": "sess_unauth",
        "message": "Hello"
    }, headers=bad_headers)
    assert resp.status_code == 401
    
    # 2. GET /chat/sessions
    resp = await client.get("/chat/sessions", headers=bad_headers)
    assert resp.status_code == 401
    
    # 3. GET /chat/sessions/any_session/history
    resp = await client.get("/chat/sessions/any_session/history", headers=bad_headers)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_chat_flow_and_history_success(client):
    """
    Verifies full chat flow:
    - User A registers & logs in.
    - Sends message to /chat, session is created under User A.
    - User A can retrieve list of sessions and individual session history.
    """
    # 1. Setup User A
    user_a, headers_a = await register_and_login(client, "A")
    session_id = "session_user_a_01"
    
    # 2. Send message
    chat_resp = await client.post("/chat", json={
        "session_id": session_id,
        "message": "Tôi muốn kiểm tra số dư ví"
    }, headers=headers_a)
    
    assert chat_resp.status_code == 200
    data = chat_resp.json().get("data", chat_resp.json())
    assert "answer" in data
    assert data["intent"] == "BALANCE_INQUIRY"
    
    # 3. List sessions
    sessions_resp = await client.get("/chat/sessions", headers=headers_a)
    assert sessions_resp.status_code == 200
    sessions = sessions_resp.json().get("data", sessions_resp.json())
    assert len(sessions) > 0
    assert sessions[0]["session_id"] == session_id
    assert sessions[0]["user_id"] == user_a["user_id"]
    
    # 4. View history
    history_resp = await client.get(f"/chat/sessions/{session_id}/history", headers=headers_a)
    assert history_resp.status_code == 200
    history = history_resp.json().get("data", history_resp.json())
    assert len(history) >= 2 # User message + assistant response
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "Tôi muốn kiểm tra số dư ví"
    assert history[1]["role"] == "assistant"
    assert history[1]["intent"] == "BALANCE_INQUIRY"


@pytest.mark.asyncio
async def test_chat_session_ownership_authorization(client):
    """
    Verifies security boundaries:
    - User A creates a session.
    - User B cannot view User A's session history (returns 403).
    - View non-existent session returns 404.
    """
    # 1. Setup User A and User B
    _, headers_a = await register_and_login(client, "A")
    _, headers_b = await register_and_login(client, "B")
    
    session_id = "session_user_a_private"
    
    # 2. User A chats
    chat_resp = await client.post("/chat", json={
        "session_id": session_id,
        "message": "Hello system"
    }, headers=headers_a)
    assert chat_resp.status_code == 200
    
    # 3. User B tries to access User A's session history -> 403 Forbidden
    history_b_resp = await client.get(f"/chat/sessions/{session_id}/history", headers=headers_b)
    assert history_b_resp.status_code == 403
    assert history_b_resp.json()["message"] == "Bạn không có quyền truy cập lịch sử của phiên hội thoại này."
    assert history_b_resp.json()["error_code"] == "FORBIDDEN_ACCESS"
    
    # 4. User A tries to access non-existent session -> 404 Not Found
    not_found_resp = await client.get("/chat/sessions/session_not_exist/history", headers=headers_a)
    assert not_found_resp.status_code == 404
    assert not_found_resp.json()["message"] == "Phiên hội thoại không tồn tại."
    assert not_found_resp.json()["error_code"] == "RESOURCE_NOT_FOUND"
