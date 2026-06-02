import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
from app.config import settings
from app.database import get_db

API_PREFIX = settings.API_V1_STR  # /api/v1

class MockChunk:
    def __init__(self, id, score, text, metadata):
        self.id = id
        self.score = score
        self.text = text
        self.metadata = metadata

async def register_and_login_user(client: AsyncClient, phone: str, role: str = "user"):
    """
    Helper to register a user with custom role and log in to get a JWT access token.
    """
    # 1. Register User
    user_resp = await client.post(f"{API_PREFIX}/finance/users", json={
        "full_name": f"User {phone}",
        "phone": phone,
        "email": f"user_{phone}@example.com",
        "password": "password123",
        "role": role
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
async def test_admin_authorization(client: AsyncClient):
    """
    Normal users should be forbidden from accessing admin endpoints.
    Admin/CSKH users should be allowed access.
    """
    # Create normal user
    _, normal_headers = await register_and_login_user(client, "0982222222", "user")
    # Create admin user
    _, admin_headers = await register_and_login_user(client, "0983333333", "admin")

    # 1. Test GET /api/v1/admin/support-tickets
    resp = await client.get("/api/v1/admin/support-tickets", headers=normal_headers)
    assert resp.status_code == 403
    
    resp = await client.get("/api/v1/admin/support-tickets", headers=admin_headers)
    assert resp.status_code == 200

    # 2. Test GET /api/v1/admin/chat-sessions/some_session/messages
    resp = await client.get("/api/v1/admin/chat-sessions/some_session/messages", headers=normal_headers)
    assert resp.status_code == 403
    
    # 3. Test POST /api/v1/admin/chat-sessions/some_session/reply
    resp = await client.post("/api/v1/admin/chat-sessions/some_session/reply", json={"message": "hi"}, headers=normal_headers)
    assert resp.status_code == 403

@pytest.mark.asyncio
async def test_chat_session_status_transitions_and_admin_flow(client: AsyncClient):
    """
    Validates:
    - Default status is BOT_ACTIVE.
    - Escalation transitions status to WAITING_HUMAN.
    - Admin reply transitions status to HUMAN_ACTIVE, updates ticket to PENDING, sets assigned_agent_id.
    - Logs tracing details to MongoDB agent_traces.
    """
    user, user_headers = await register_and_login_user(client, "0984444444", "user")
    admin, admin_headers = await register_and_login_user(client, "0985555555", "admin")
    
    session_id = "sess_admin_test_1"

    # Mock RAG retrieve to return chunks with a high score so context_insufficient is False
    mock_chunks = [
        MockChunk(
            id="chunk_1",
            score=0.9,
            text="Phí chuyển khoản là 0 VND, phí rút tiền là 1,100 VND.",
            metadata={"source": "tai_lieu.pdf", "category": "Biểu phí"}
        )
    ]

    with patch("app.modules.rag.retriever.RAGRetriever.retrieve", new_callable=AsyncMock) as mock_retrieve:
        mock_retrieve.return_value = mock_chunks

        # Step 1: Normal chat. Default status should be BOT_ACTIVE.
        resp = await client.post("/chat", json={
            "session_id": session_id,
            "message": "Chào bạn, tôi cần tra cứu phí chuyển khoản"
        }, headers=user_headers)
        assert resp.status_code == 200
        
        # Verify session status is BOT_ACTIVE
        sessions_resp = await client.get("/chat/sessions", headers=user_headers)
        assert sessions_resp.status_code == 200
        sessions_data = sessions_resp.json()
        test_session = next((s for s in sessions_data if s["session_id"] == session_id), None)
        assert test_session is not None
        assert test_session["status"] == "BOT_ACTIVE"

        # Step 2: Escalation message. Should trigger escalation support ticket and WAITING_HUMAN status.
        esc_resp = await client.post("/chat", json={
            "session_id": session_id,
            "message": "Tôi bị mất tiền lừa đảo, tài khoản ví bị hack rồi"
        }, headers=user_headers)
        assert esc_resp.status_code == 200
        assert esc_resp.json()["escalation"]["required"] is True

        # Verify session status is now WAITING_HUMAN
        sessions_resp = await client.get("/chat/sessions", headers=user_headers)
        test_session = next((s for s in sessions_resp.json() if s["session_id"] == session_id), None)
        assert test_session["status"] == "WAITING_HUMAN"

        # Step 3: CSKH Dashboard APIs
        # Admin gets all support tickets
        tickets_resp = await client.get("/api/v1/admin/support-tickets", headers=admin_headers)
        assert tickets_resp.status_code == 200
        tickets = tickets_resp.json()["data"]
        linked_ticket = next((t for t in tickets if t["session_id"] == session_id), None)
        assert linked_ticket is not None
        assert linked_ticket["status"] == "OPEN"
        assert linked_ticket["assigned_agent_id"] is None

        # Admin reads chat history of this session (unrestricted)
        history_resp = await client.get(f"/api/v1/admin/chat-sessions/{session_id}/messages", headers=admin_headers)
        assert history_resp.status_code == 200
        history = history_resp.json()
        assert len(history) >= 2

        # Step 4: Admin replies to chat
        reply_resp = await client.post(f"/api/v1/admin/chat-sessions/{session_id}/reply", json={
            "message": "Chào bạn, tôi đã tiếp nhận sự cố ví bị hack của bạn và đang kiểm tra."
        }, headers=admin_headers)
        assert reply_resp.status_code == 200
        assert reply_resp.json()["data"]["status"] == "HUMAN_ACTIVE"

        # Verify session status is now HUMAN_ACTIVE
        sessions_resp = await client.get("/chat/sessions", headers=user_headers)
        test_session = next((s for s in sessions_resp.json() if s["session_id"] == session_id), None)
        assert test_session["status"] == "HUMAN_ACTIVE"

        # Verify ticket status is now PENDING and assigned_agent_id is set
        tickets_resp2 = await client.get("/api/v1/admin/support-tickets", headers=admin_headers)
        tickets2 = tickets_resp2.json()["data"]
        linked_ticket2 = next((t for t in tickets2 if t["session_id"] == session_id), None)
        assert linked_ticket2["status"] == "PENDING"
        assert linked_ticket2["assigned_agent_id"] == admin["user_id"]

        # Step 5: Verify Agent Tracing document was successfully persisted in MongoDB
        db = get_db()
        assert db is not None
        trace = await db["agent_traces"].find_one({"session_id": session_id})
        assert trace is not None
        assert "request_id" in trace
        assert "latency_ms" in trace
        assert trace["intent"] is not None
        assert trace["confidence"] is not None
        assert isinstance(trace["retrieved_chunks"], list)
