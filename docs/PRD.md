# Product Requirements Document (PRD) - VSmartPay AI Support Agent

## 1. Mục tiêu sản phẩm
Xây dựng một chatbot hỗ trợ khách hàng thông minh dành riêng cho ví điện tử VSmartPay. Chatbot sử dụng mô hình RAG để tra cứu tài liệu nghiệp vụ (FAQ, biểu phí, hạn mức) và phân loại ý định người dùng nhằm tối ưu hóa hoạt động CSKH.

## 2. Các tính năng chính
- **Hội thoại thông minh (Chat)**: Giao tiếp tự nhiên bằng tiếng Việt qua mô hình LLM kết hợp RAG.
- **Truy xuất thông tin ví (Financial Tools)**: Tra cứu số dư tài khoản, lịch sử giao dịch và biểu phí tự động qua Mock Wallet API.
- **Phân loại ý định (Intent Classification)**: Định tuyến câu hỏi chính xác để trả lời hoặc thực thi công cụ thích hợp.
- **Chuyển tiếp nhân viên hỗ trợ (Human Escalation)**: Tự động phát hiện các yêu cầu khẩn cấp, nhạy cảm hoặc khiếu nại để chuyển giao cho nhân viên thật xử lý theo chính sách bảo mật.
