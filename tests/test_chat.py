import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "VSmartPay AI Support Agent"

def test_chat_endpoint_placeholder():
    payload = {
        "user_id": "usr_001",
        "message": "Xin chào VSmartPay",
        "session_id": "session_test"
    }
    response = client.post("/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "VSmartPay AI Support Agent is not fully configured yet."
    assert "intent" in data
    assert data["sources"] == []
    assert data["tool_calls"] == []
    assert "escalation" in data
    assert "required" in data["escalation"]

def test_tools_balance():
    response = client.get("/tools/balance/usr_001")
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "usr_001"
    assert "balance" in data
    assert data["currency"] == "VND"

def test_tools_transactions():
    response = client.get("/tools/transactions/tx_001")
    assert response.status_code == 200
    data = response.json()
    assert data["transaction_id"] == "tx_001"
    assert "amount" in data
    assert "status" in data

def test_tools_fees():
    response = client.get("/tools/fees")
    assert response.status_code == 200
    data = response.json()
    assert "transfer_fee" in data
    assert "withdrawal_fee" in data
    assert "deposit_fee" in data
