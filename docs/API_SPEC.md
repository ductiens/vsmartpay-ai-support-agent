# Đặc tả Tài liệu API (API Specification)

Tài liệu này mô tả chi tiết toàn bộ các cổng kết nối (endpoints) của hệ thống VSmartPay AI Support Agent.

---

## 1. Chat API (`POST /chat`)
Cổng tiếp nhận tin nhắn hội thoại từ người dùng.

### Request Body (`application/json`):
```json
{
  "session_id": "sess_user_001",
  "user_id": "user_001",
  "message": "Số dư ví hiện tại của tôi còn bao nhiêu tiền?"
}
```

### Response Body (`200 OK`):
```json
{
  "answer": "Chào bạn, số dư khả dụng hiện tại trong tài khoản ví VSmartPay của bạn là 2.500.000 VND.",
  "intent": "BALANCE_INQUIRY",
  "confidence": 0.95,
  "sources": [
    {
      "doc_id": "limits.md",
      "chunk_id": "chk_limit_01",
      "title": "Hạn mức - limits.md",
      "score": 0.9
    }
  ],
  "tool_calls": [
    {
      "tool_name": "check_balance",
      "arguments": {
        "user_id": "user_001"
      },
      "result": {
        "user_id": "user_001",
        "balance": 2500000,
        "currency": "VND",
        "status": "ACTIVE"
      }
    }
  ],
  "escalation": {
    "required": false,
    "reason": null,
    "priority": null
  }
}
```

---

## 2. Tools API (`/tools`)
Cổng cung cấp các API ví điện tử giả lập để kiểm tra và xử lý.

### 2.1 Kiểm tra số dư (`GET /tools/balance/{user_id}`)
- **Tham số**: `user_id` (đường dẫn)
- **Phản hồi (`200 OK`)**:
  ```json
  {"user_id": "user_001", "balance": 2500000, "currency": "VND", "status": "ACTIVE"}
  ```

### 2.2 Tra cứu trạng thái giao dịch (`GET /tools/transactions/{transaction_id}`)
- **Tham số**: `transaction_id` (đường dẫn)
- **Phản hồi (`200 OK`)**:
  ```json
  {"transaction_id": "txn_001", "user_id": "user_001", "amount": 100000, "type": "TRANSFER", "status": "SUCCESS", "timestamp": "2026-05-28T09:00:00Z", "currency": "VND"}
  ```

### 2.3 Tra cứu biểu phí (`GET /tools/fees`)
- **Tham số**: `transaction_type` (query), `amount` (query)
- **Phản hồi (`200 OK`)**:
  ```json
  {"transaction_type": "TRANSFER", "amount": 500000, "fee": 0, "currency": "VND"}
  ```

---

## 3. Upload & Ingestion API (`POST /api/v1/documents/upload`)
Cổng nạp tài liệu mới vào cơ sở dữ liệu tri thức RAG.

### Request Body (`multipart/form-data`):
- `file`: Đối tượng file (PDF, TXT, DOCX, MD)
- `category`: Thể loại tài liệu (Ví dụ: `Hạn mức`)
- `kb_type`: Loại dữ liệu (`faq` / `policy` / `product`)
- `agent_scope`: Phạm vi tìm kiếm (`limits` / `fees` / `security` / `general` / `transfer`)

### Response Body (`200 OK`):
```json
{
  "success": true,
  "message": "Nạp tài liệu thành công!",
  "chunks_count": 8
}
```

---

## 4. Status Polling API (`GET /tools/transactions/{transaction_id}/poll`)
API kiểm tra và thăm dò (polling) liên tục trạng thái giao dịch đang xử lý.
- **Tham số**: `transaction_id` (đường dẫn)
- **Phản hồi (`200 OK`)**:
  ```json
  {
    "transaction_id": "txn_002",
    "status": "PENDING",
    "should_poll_again": true,
    "elapsed_seconds": 15
  }
  ```
