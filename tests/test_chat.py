import pytest
from unittest.mock import patch, MagicMock

@pytest.mark.asyncio
async def test_health_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json().get("data", response.json())
    assert data["status"] == "ok"
    assert data["service"] == "VSmartPay AI Support Agent"


@pytest.mark.asyncio
@patch("app.modules.rag.embeddings.EmbeddingService.get_embedding")
@patch("openai.resources.chat.completions.AsyncCompletions.create")
async def test_chat_endpoint_success(mock_chat_create, mock_get_embedding, client):
    # Mock OpenAI Embeddings call
    mock_get_embedding.return_value = [0.01] * 1536
    
    # Mock OpenAI Chat Completions call
    mock_choice = MagicMock()
    mock_choice.message.content = "Hạn mức giao dịch tối đa qua ví VSmartPay là 50.000.000 VND/ngày đối với tài khoản đã KYC."
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_chat_create.return_value = mock_response

    # Request parameters
    payload = {
        "session_id": "sess_unit_test_01",
        "user_id": "user_unit_test_01",
        "message": "Hạn mức giao dịch một ngày là bao nhiêu?"
    }

    # Call POST /chat
    response = await client.post("/chat", json=payload)
    assert response.status_code == 200
    
    data = response.json().get("data", response.json())
    assert "answer" in data
    assert "Hạn mức giao dịch tối đa" in data["answer"]
    assert data["intent"] == "LIMIT_INQUIRY" # Matches keyword 'hạn mức'
    assert data["confidence"] == 0.9
    assert len(data["sources"]) > 0
    assert data["sources"][0]["doc_id"] == "limits.md" # Mock search returns default limits chunk
    assert data["escalation"]["required"] is False


@pytest.mark.asyncio
@patch("app.modules.rag.embeddings.EmbeddingService.get_embedding")
@patch("openai.resources.chat.completions.AsyncCompletions.create")
async def test_chat_endpoint_escalation_fraud(mock_chat_create, mock_get_embedding, client):
    # Mock OpenAI calls
    mock_get_embedding.return_value = [0.01] * 1536
    mock_choice = MagicMock()
    mock_choice.message.content = "Tài khoản của bạn đã được tiếp nhận thông báo nghi ngờ lừa đảo."
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_chat_create.return_value = mock_response

    payload = {
        "session_id": "sess_unit_test_02",
        "user_id": "user_unit_test_02",
        "message": "Tôi nghi ngờ tài khoản bị lừa đảo mất tiền"
    }

    response = await client.post("/chat", json=payload)
    assert response.status_code == 200
    
    data = response.json().get("data", response.json())
    assert data["intent"] == "FRAUD_OR_SCAM_REPORT" # Matches keywords
    assert data["escalation"]["required"] is True
    assert data["escalation"]["priority"] == "HIGH"


@pytest.mark.asyncio
async def test_tools_balance_endpoint(client):
    response = await client.get("/tools/balance/usr_001")
    assert response.status_code == 200
    data = response.json().get("data", response.json())
    assert data["user_id"] == "usr_001"
    assert data["balance"] == 2500000
    assert data["currency"] == "VND"


@pytest.mark.asyncio
async def test_tools_transactions_endpoint(client):
    response = await client.get("/tools/transactions/tx_001")
    assert response.status_code == 200
    data = response.json().get("data", response.json())
    assert data["transaction_id"] == "tx_001"
    assert data["amount"] == 100000
    assert data["status"] == "SUCCESS"


@pytest.mark.asyncio
async def test_tools_fees_endpoint(client):
    response = await client.get("/tools/fees")
    assert response.status_code == 200
    data = response.json().get("data", response.json())
    assert data["transfer_fee"] == 0
    assert data["withdrawal_fee"] == 1100
    assert data["deposit_fee"] == 0


@pytest.mark.asyncio
@patch("app.modules.tools.financial_tools.MockWalletClient.get_transaction_by_id")
async def test_tools_transaction_not_found(mock_get_tx_by_id, client):
    mock_get_tx_by_id.return_value = None
    response = await client.get("/tools/transactions/non_existent_tx_id")
    assert response.status_code == 404
    data = response.json().get("data", response.json())
    assert data["success"] is False
    assert data["error_code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.asyncio
@patch("app.modules.tools.financial_tools.MockWalletClient.get_wallet_by_user_id")
async def test_tools_balance_not_found(mock_get_wallet, client):
    mock_get_wallet.return_value = None
    response = await client.get("/tools/balance/non_existent_user_id")
    assert response.status_code == 404
    data = response.json().get("data", response.json())
    assert data["success"] is False
    assert data["error_code"] == "RESOURCE_NOT_FOUND"
