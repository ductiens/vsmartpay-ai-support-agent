import pytest
from app.config import settings

@pytest.mark.asyncio
async def test_chat_endpoint_validation_error(client):
    # Invalid request payload (missing fields)
    payload = {
        "user_id": "usr_01"
    }
    response = await client.post("/chat", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert data["error_code"] == "VALIDATION_ERROR"

@pytest.mark.asyncio
async def test_chat_endpoint_legacy_flow(client):
    # Ensure USE_LANGGRAPH is False
    settings.USE_LANGGRAPH = False
    
    payload = {
        "session_id": "sess_api_legacy",
        "user_id": "user_001",
        "message": "Tôi muốn kiểm tra số dư ví"
    }
    
    response = await client.post("/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "BALANCE_INQUIRY"
    assert "answer" in data
    assert len(data["tool_calls"]) > 0

@pytest.mark.asyncio
async def test_chat_endpoint_langgraph_flow(client):
    # Temporarily set USE_LANGGRAPH to True
    settings.USE_LANGGRAPH = True
    try:
        payload = {
            "session_id": "sess_api_lg",
            "user_id": "user_001",
            "message": "Tôi muốn kiểm tra số dư ví"
        }
        
        response = await client.post("/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "BALANCE_INQUIRY"
        assert "answer" in data
        assert len(data["tool_calls"]) > 0
    finally:
        settings.USE_LANGGRAPH = False
