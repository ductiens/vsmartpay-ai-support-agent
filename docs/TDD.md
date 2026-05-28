# Technical Design Document (TDD) - VSmartPay AI Support Agent

## 1. Kiến trúc hệ thống
Hệ thống được thiết kế theo mô hình modular:
- **Chat Module**: Điểm tiếp nhận yêu cầu hội thoại, lưu trữ lịch sử qua MongoDB.
- **RAG Module**: Đảm nhận việc sinh embedding (qua OpenAI `text-embedding-3-small`) và lưu trữ/tìm kiếm vector tương đồng qua FAISS index cục bộ.
- **Intents Module**: Phân loại ý định khách hàng bằng các quy tắc heurictics / mô hình LLM.
- **Tools Module**: Thực thi các truy vấn tài chính (số dư, giao dịch) thông qua API kết nối Mock Wallet.
- **Escalation Module**: Đánh giá và kiểm tra chính sách an toàn bảo mật để kích hoạt cơ chế chuyển tiếp sang nhân viên hỗ trợ.

## 2. Lưu đồ xử lý (Chat Flow)
1. Người dùng gửi câu hỏi qua `POST /chat`.
2. Hệ thống phân loại intent thông qua `IntentClassifier`.
3. Nếu thuộc nhóm khẩn cấp, kích hoạt `EscalationService` chuyển sang chế độ chuyển tiếp nhân viên.
4. Nếu thuộc nhóm tra cứu thông tin cá nhân, thực thi gọi `ToolService` truy vấn mock dữ liệu.
5. Ngược lại, thực hiện truy xuất tri thức qua RAG và LLM để tổng hợp phản hồi và trả về cho người dùng.
