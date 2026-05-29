import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.database import get_db

@pytest.mark.asyncio
async def test_tools_balance_mock_wallet(client):
    """Verify GET /tools/balance/{user_id} returns the correct user_001 mock data."""
    response = await client.get("/tools/balance/user_001")
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "user_001"
    assert data["balance"] == 2500000
    assert data["currency"] == "VND"


@pytest.mark.asyncio
async def test_tools_transactions_mock_wallet(client):
    """Verify GET /tools/transactions/{transaction_id} returns correct status details."""
    # txn_001 (SUCCESS)
    response = await client.get("/tools/transactions/txn_001")
    assert response.status_code == 200
    data = response.json()
    assert data["transaction_id"] == "txn_001"
    assert data["status"] == "SUCCESS"
    assert data["amount"] == 100000
    
    # txn_002 (PENDING)
    response = await client.get("/tools/transactions/txn_002")
    assert response.status_code == 200
    data = response.json()
    assert data["transaction_id"] == "txn_002"
    assert data["status"] == "PENDING"
    
    # txn_003 (FAILED)
    response = await client.get("/tools/transactions/txn_003")
    assert response.status_code == 200
    data = response.json()
    assert data["transaction_id"] == "txn_003"
    assert data["status"] == "FAILED"


@pytest.mark.asyncio
async def test_tools_fees_mock_wallet(client):
    """Verify GET /tools/fees?transaction_type=TRANSFER&amount=500000 returns correct fee info."""
    response = await client.get("/tools/fees?transaction_type=TRANSFER&amount=500000")
    assert response.status_code == 200
    data = response.json()
    assert data["transaction_type"] == "TRANSFER"
    assert data["amount"] == 500000
    assert data["fee"] == 0
    assert data["currency"] == "VND"


@pytest.mark.asyncio
@patch("app.modules.rag.embeddings.EmbeddingService.get_embedding")
async def test_chat_balance_tool_call(mock_get_embedding, client):
    """Verify that /chat automatically calls check_balance tool on BALANCE_INQUIRY intent."""
    mock_get_embedding.return_value = [0.01] * 1536
    
    payload = {
        "session_id": "sess_tool_01",
        "user_id": "user_001",
        "message": "Tôi muốn kiểm tra số dư ví khả dụng hiện tại của mình là bao nhiêu?"
    }
    
    response = await client.post("/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert data["intent"] == "BALANCE_INQUIRY"
    
    # Check tool calls list
    tool_calls = data["tool_calls"]
    assert len(tool_calls) > 0
    assert tool_calls[0]["tool_name"] == "check_balance"
    assert tool_calls[0]["arguments"]["user_id"] == "user_001"
    assert tool_calls[0]["result"]["balance"] == 2500000


@pytest.mark.asyncio
@patch("app.modules.rag.embeddings.EmbeddingService.get_embedding")
async def test_chat_transaction_status_tool_call(mock_get_embedding, client):
    """Verify /chat extracts transaction_id and calls get_transaction_status tool."""
    mock_get_embedding.return_value = [0.01] * 1536
    
    payload = {
        "session_id": "sess_tool_02",
        "user_id": "user_001",
        "message": "Trạng thái giao dịch mã txn_001 như thế nào?"
    }
    
    response = await client.post("/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "TRANSACTION_STATUS"
    
    tool_calls = data["tool_calls"]
    assert len(tool_calls) > 0
    assert tool_calls[0]["tool_name"] == "get_transaction_status"
    assert tool_calls[0]["arguments"]["transaction_id"] == "txn_001"
    assert tool_calls[0]["result"]["status"] == "SUCCESS"


@pytest.mark.asyncio
@patch("app.modules.rag.embeddings.EmbeddingService.get_embedding")
async def test_chat_fee_tool_call(mock_get_embedding, client):
    """Verify /chat extracts amount/type and calls get_fee tool."""
    mock_get_embedding.return_value = [0.01] * 1536
    
    payload = {
        "session_id": "sess_tool_03",
        "user_id": "user_001",
        "message": "Biểu phí khi chuyển tiền số tiền 500k qua ví là bao nhiêu?"
    }
    
    response = await client.post("/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "FEE_INQUIRY"
    
    tool_calls = data["tool_calls"]
    assert len(tool_calls) > 0
    assert tool_calls[0]["tool_name"] == "get_fee"
    assert tool_calls[0]["arguments"]["transaction_type"] == "TRANSFER"
    assert tool_calls[0]["arguments"]["amount"] == 500000
    assert tool_calls[0]["result"]["fee"] == 0


@pytest.mark.asyncio
@patch("app.modules.rag.embeddings.EmbeddingService.get_embedding")
async def test_chat_escalation_security_keywords(mock_get_embedding, client):
    """Verify /chat escalates on high-risk keywords (lost money, OTP leak) and saves ticket to MongoDB."""
    mock_get_embedding.return_value = [0.01] * 1536
    
    payload = {
        "session_id": "sess_esc_01",
        "user_id": "user_001",
        "message": "Tài khoản của tôi bị trừ tiền không rõ lý do, nghi ngờ bị hack và lộ mã otp!"
    }
    
    response = await client.post("/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    # Check escalation detail in response
    esc = data["escalation"]
    assert esc["required"] is True
    assert esc["priority"] == "HIGH"
    
    # Verify support ticket was created in tool_calls
    tool_calls = data["tool_calls"]
    ticket_tool = next((tc for tc in tool_calls if tc["tool_name"] == "create_support_ticket"), None)
    assert ticket_tool is not None
    assert ticket_tool["arguments"]["user_id"] == "user_001"
    assert ticket_tool["arguments"]["issue_type"] in ["FRAUD", "SECURITY"]
    
    # Verify ticket was actually inserted into MongoDB 'escalation_tickets' collection
    db = get_db()
    inserted_ticket = await db["escalation_tickets"].find_one({"user_id": "user_001"})
    assert inserted_ticket is not None
    assert inserted_ticket["ticket_id"] == ticket_tool["result"]["ticket_id"]
    assert inserted_ticket["status"] == "OPEN"
