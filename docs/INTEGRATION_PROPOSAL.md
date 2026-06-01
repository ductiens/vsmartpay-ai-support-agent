# Đề xuất Tích hợp Hệ thống (App Integration & Deployment Proposal)

Tài liệu này đề xuất phương án chi tiết để tích hợp VSmartPay AI Support Agent vào ứng dụng di động (Mobile App) và hệ thống hỗ trợ vận hành (Human CRM) hiện tại của VSmartPay.

---

## 1. Sơ đồ luồng tích hợp tổng quan (Architecture Overview)

Chatbot ảo sẽ được đặt làm lớp trung gian xử lý tin nhắn đầu tiên (Tier 1 Support). Hệ thống kết nối qua cổng Webhook Gateway để giao tiếp giữa Mobile App và Chatbot Service.

```text
 [ Mobile App ] ──(HTTPS/Websocket)──► [ Webhook Gateway ]
                                              │
                                              ▼ (HTTP POST)
                                     [ AI Support Agent ]
                                              │
                   ┌──────────────────────────┴──────────────────────────┐
                   ▼ (Answer Found)                                      ▼ (Escalated/Ticket)
           [ Send Response ]                                   [ CRM Gateway ]
                   │                                                     │
                   ▼                                                     ▼
             [ Mobile App ]                                     [ Human Agent Portal ]
                                                                (Nhân viên CSKH tiếp nhận)
```

---

## 2. Đặc tả dữ liệu Webhook (Webhook Payload Specifications)

### 2.1 Tin nhắn từ Mobile App gửi đi (Inbound Event)
- **Phương thức**: `POST`
- **URL**: `https://api.vsmartpay.vn/webhook/inbound`
- **Payload JSON**:
  ```json
  {
    "event_id": "evt_abc123",
    "session_id": "sess_user_999",
    "user_id": "usr_999",
    "message_content": "Tôi muốn rút tiền mặt từ ví tại cây ATM Techcombank thì hạn mức là bao nhiêu?",
    "timestamp": 1779998887
  }
  ```

### 2.2 Phản hồi gửi ngược lại Mobile App (Outbound Event)
- **Payload JSON**:
  ```json
  {
    "event_id": "evt_out_xyz789",
    "session_id": "sess_user_999",
    "answer": "Theo tài liệu chính sách hạn mức của ví VSmartPay, hạn mức rút tiền mặt tối đa của bạn là 10.000.000 VND/ngày.",
    "intent": "LIMIT_INQUIRY",
    "escalated": false,
    "timestamp": 1779998889
  }
  ```

---

## 3. Quy trình chuyển tiếp nhân viên CSKH (Escalation & Ticket Handoff)

Khi Chatbot ảo phát hiện cần chuyển giao hỗ trợ CSKH:
1. **Tạo Ticket**: AI Agent tự động gọi `create_support_ticket` để lưu thông tin sự cố của người dùng (lý do, lịch sử trò chuyện) vào bộ sưu tập `escalation_tickets` của MongoDB.
2. **Đẩy Event Handoff**: AI Agent bắn một Event tới Webhook Gateway:
   ```json
   {
     "event_type": "HUMAN_HANDOFF_REQUIRED",
     "user_id": "usr_999",
     "session_id": "sess_user_999",
     "ticket_id": "tkt_xyz123",
     "priority": "HIGH",
     "reason": "Báo cáo lộ mã OTP và mất tiền tài khoản."
   }
   ```
3. **Phân phối cuộc gọi**: Webhook Gateway chuyển tiếp sự kiện này đến hệ thống CRM để phân bổ cho nhân viên CSKH trực tổng đài rảnh gần nhất tiếp quản cuộc chat.

---

## 4. Kế hoạch triển khai & Giám sát (Deployment & Monitoring)

- **Bước 1 (Staging Deployment)**: Triển khai Chatbot dạng Container Docker trên môi trường Staging Kubernetes, liên kết với MongoDB Atlas Sandbox và mock ví API.
- **Bước 2 (A/B Testing)**: Cấu hình Webhook định tuyến **10% lưu lượng chat** thực tế của người dùng qua Chatbot ảo để quan sát độ chính xác của phân loại ý định và thời gian phản hồi.
- **Bước 3 (Full Rollout)**: Mở rộng quy mô lên 100% lưu lượng, thiết lập hệ thống giám sát thời gian phản hồi (p95 latency) và cảnh báo tự động qua Slack/Telegram khi p95 vượt quá 3.0 giây.
