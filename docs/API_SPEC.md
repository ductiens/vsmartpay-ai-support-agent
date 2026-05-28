# API Specifications - VSmartPay AI Support Agent

## 1. Health check
- **Endpoint**: `GET /health`
- **Response**:
  ```json
  {
    "status": "ok",
    "service": "VSmartPay AI Support Agent"
  }
  ```

## 2. Chat API
- **Endpoint**: `POST /chat`
- **Request Body**:
  ```json
  {
    "user_id": "usr_001",
    "message": "Phí chuyển tiền là bao nhiêu?",
    "session_id": "session_abc"
  }
  ```
- **Response Body**:
  ```json
  {
    "answer": "Chuyển tiền từ ví sang ví qua VSmartPay được miễn phí hoàn toàn không giới hạn.",
    "intent": "FAQ_FEES",
    "sources": ["fees.md"],
    "tool_calls": [],
    "escalation": {
      "required": false,
      "reason": null
    }
  }
  ```

## 3. Financial Tools
- **Endpoint**: `GET /tools/balance/{user_id}`
- **Endpoint**: `GET /tools/transactions/{transaction_id}`
- **Endpoint**: `GET /tools/fees`
