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
    user_resp = await client.post(f"{API_PREFIX}/users", json={
        "full_name": f"User {phone}",
        "phone": phone,
        "email": f"user_{phone}@example.com",
        "password": "password123",
    })
    assert user_resp.status_code == 201
    user_data = user_resp.json()["data"]

    if role != "user":
        db = get_db()
        await db["users"].update_one(
            {"user_id": user_data["user_id"]},
            {"$set": {"role": role}}
        )
        user_data["role"] = role

    login_resp = await client.post(f"{API_PREFIX}/login", json={
        "phone": phone,
        "password": "password123",
    })
    assert login_resp.status_code == 200
    token_data = login_resp.json()["data"]
    access_token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    return user_data, headers

@pytest.mark.asyncio
async def test_transaction_history_intent_and_tool(client: AsyncClient):
    """
    Verifies that asking for recent transaction history correctly classifies as TRANSACTION_HISTORY
    and retrieves history data.
    """
    user, user_headers = await register_and_login_user(client, "0986666666", "user")
    session_id = "sess_hist_01"

    mock_chunks = [
        MockChunk("chunk_1", 0.9, "Lịch sử giao dịch ví VSmartPay hiển thị danh sách giao dịch gần đây.", {"source": "huong_dan.pdf"})
    ]

    with patch("app.modules.rag.retriever.RAGRetriever.retrieve", new_callable=AsyncMock) as mock_retrieve:
        mock_retrieve.return_value = mock_chunks

        # Ask for transaction history
        resp = await client.post("/chat", json={
            "session_id": session_id,
            "message": "Cho tôi xem lịch sử các giao dịch gần đây của tôi"
        }, headers=user_headers)
        
        assert resp.status_code == 200
        data = resp.json().get("data", resp.json())
        assert data["intent"] == "TRANSACTION_HISTORY"
        
        tool_calls = data["tool_calls"]
        assert len(tool_calls) > 0
        assert tool_calls[0]["tool_name"] == "get_transaction_history"
        assert tool_calls[0]["arguments"]["user_id"] == user["user_id"]

@pytest.mark.asyncio
async def test_transaction_status_security_constraint(client: AsyncClient):
    """
    Ensures that transaction status lookup is strictly protected and checked for ownership.
    - User A can view User A's transaction.
    - User B cannot view User A's transaction.
    """
    user_a, headers_a = await register_and_login_user(client, "0987777777", "user")
    user_b, headers_b = await register_and_login_user(client, "0988888888", "user")
    
    # Create wallet for User A to perform deposit
    await client.post(f"{API_PREFIX}/wallets", json={"currency": "VND"}, headers=headers_a)
    
    # User A deposits money
    dep_resp = await client.post(f"{API_PREFIX}/transactions", json={
        "amount": 100000,
        "type": "DEPOSIT",
        "description": "Nạp tiền User A"
    }, headers=headers_a)
    assert dep_resp.status_code == 201
    txn_id = dep_resp.json()["data"]["transaction_id"]

    mock_chunks = [MockChunk("chunk_1", 0.95, "Trạng thái giao dịch ví.", {"source": "huong_dan.pdf"})]

    with patch("app.modules.rag.retriever.RAGRetriever.retrieve", new_callable=AsyncMock) as mock_retrieve:
        mock_retrieve.return_value = mock_chunks

        # 1. User A queries User A's transaction -> Allowed
        a_resp = await client.post("/chat", json={
            "session_id": "sess_txn_a",
            "message": f"Hãy xem trạng thái của mã giao dịch {txn_id}"
        }, headers=headers_a)
        assert a_resp.status_code == 200
        assert "thành công" in a_resp.json()["data"]["answer"].lower() or "success" in a_resp.json()["data"]["answer"].lower()

        # 2. User B queries User A's transaction -> Rejected with security error
        b_resp = await client.post("/chat", json={
            "session_id": "sess_txn_b",
            "message": f"Kiểm tra giúp tôi giao dịch {txn_id}"
        }, headers=headers_b)
        assert b_resp.status_code == 200
        assert "không có quyền" in b_resp.json()["data"]["answer"] or "no permission" in b_resp.json()["data"]["answer"].lower()

@pytest.mark.asyncio
async def test_admin_reply_human_agent_endpoint(client: AsyncClient):
    """
    Verifies POST /api/v1/admin/chat-sessions/{session_id}/messages.
    Checks:
    - Saves message in DB with role="assistant" and sender="HUMAN_AGENT".
    - Automatically updates chat session status to HUMAN_ACTIVE.
    """
    user, user_headers = await register_and_login_user(client, "0981112222", "user")
    admin, admin_headers = await register_and_login_user(client, "0983334444", "admin")
    session_id = "sess_reply_human"

    # Create session and trigger escalation
    mock_chunks = [MockChunk("chunk_1", 0.9, "Chính sách.", {"source": "huong_dan.pdf"})]
    with patch("app.modules.rag.retriever.RAGRetriever.retrieve", new_callable=AsyncMock) as mock_retrieve:
        mock_retrieve.return_value = mock_chunks

        # Escalation message -> sets session status to WAITING_HUMAN
        esc_resp = await client.post("/chat", json={
            "session_id": session_id,
            "message": "Tôi bị mất điện thoại và mất sạch tiền trong ví rồi"
        }, headers=user_headers)
        assert esc_resp.status_code == 200

    # CSKH replies using the custom message endpoint
    msg_resp = await client.post(f"/api/v1/admin/chat-sessions/{session_id}/messages", json={
        "message": "Chúng tôi đang phong tỏa tài khoản của bạn để xác minh sự cố.",
        "sender": "HUMAN_AGENT"
    }, headers=admin_headers)
    assert msg_resp.status_code == 200

    # Verify session status is HUMAN_ACTIVE
    sessions_resp = await client.get("/chat/sessions", headers=user_headers)
    test_session = next((s for s in sessions_resp.json().get("data", sessions_resp.json()) if s["session_id"] == session_id), None)
    assert test_session["status"] == "HUMAN_ACTIVE"

    # Verify that the message in DB has sender=="HUMAN_AGENT"
    db = get_db()
    messages = await db["chat_messages"].find({"session_id": session_id, "role": "assistant"}).to_list(length=10)
    # The last message should be the HUMAN_AGENT one
    human_msg = next((m for m in messages if m.get("sender") == "HUMAN_AGENT"), None)
    assert human_msg is not None
    assert human_msg["content"] == "Chúng tôi đang phong tỏa tài khoản của bạn để xác minh sự cố."
