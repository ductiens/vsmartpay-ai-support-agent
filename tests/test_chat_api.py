import pytest

@pytest.mark.asyncio
async def test_chat_endpoint_validation_error(client):
    # Invalid request payload (missing fields)
    payload = {
        "user_id": "usr_01"
    }
    response = await client.post("/chat", json=payload)
    assert response.status_code == 422
    data = response.json().get("data", response.json())
    assert data["success"] is False
    assert data["error_code"] == "VALIDATION_ERROR"

@pytest.mark.asyncio
async def test_chat_endpoint_langgraph_flow(client):
    payload = {
        "session_id": "sess_api_lg",
        "user_id": "user_001",
        "message": "Tôi muốn kiểm tra số dư ví"
    }
    
    response = await client.post("/chat", json=payload)
    assert response.status_code == 200
    data = response.json().get("data", response.json())
    assert data["intent"] == "BALANCE_INQUIRY"
    assert "answer" in data
    assert len(data["tool_calls"]) > 0

@pytest.mark.asyncio
async def test_chat_endpoint_session_id_generation(client):
    # Payload without session_id
    payload = {
        "user_id": "user_001",
        "message": "Tôi muốn kiểm tra số dư ví"
    }
    
    response = await client.post("/chat", json=payload)
    assert response.status_code == 200
    data = response.json().get("data", response.json())
    assert "session_id" in data
    assert data["session_id"].startswith("sess_")
    assert data["intent"] == "BALANCE_INQUIRY"
    assert "answer" in data
