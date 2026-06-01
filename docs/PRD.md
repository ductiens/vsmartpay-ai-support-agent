# Yêu cầu Sản phẩm (Product Requirements Document - PRD)

**Dự án**: VSmartPay AI Support Agent  
**Phiên bản**: 1.0.0  
**Tác giả**: VSmartPay Product Team  

---

## 1. Mục tiêu Sản phẩm (Product Goals)
Mục tiêu là xây dựng một **Trợ lý hỗ trợ khách hàng ảo (AI Support Agent)** thông minh và tin cậy cho ví điện tử VSmartPay nhằm giải quyết tự động lên tới **80% câu hỏi thường gặp** của người dùng, bao gồm: tra cứu số dư, kiểm tra trạng thái giao dịch, hướng dẫn nạp/rút/chuyển tiền, và giải thích biểu phí. 

Đồng thời, hệ thống có khả năng tự động phát hiện các rủi ro bảo mật (như lộ OTP, nghi ngờ lừa đảo) hoặc các lỗi hệ thống để kịp thời chuyển giao (escalate) cho đội ngũ CSKH thật một cách an toàn và tối ưu nhất.

---

## 2. Người dùng mục tiêu & Kịch bản Nghiệp vụ (Scenarios)

### 2.1 Người dùng ví VSmartPay
Khách hàng cá nhân sử dụng ví điện tử VSmartPay trên thiết bị di động để thanh toán và giao dịch tài chính hàng ngày.
- **Kịch bản A (Tra cứu Phí & Hạn mức)**: Khách hàng hỏi "Phí rút tiền về thẻ Techcombank là bao nhiêu?". AI sẽ tự động kích hoạt truy xuất tài liệu chính sách biểu phí để đưa ra biểu phí chính xác.
- **Kịch bản B (Giao dịch gặp lỗi)**: Khách hàng hỏi "Tôi chuyển tiền mã txn_003 bị báo lỗi nhưng tài khoản vẫn bị trừ tiền?". AI tự động phân loại ý định `FAILED_TRANSACTION`, truy vấn thông tin ví giả lập, phát hiện lỗi giao dịch và kích hoạt chèn ticket CSKH vào MongoDB để hỗ trợ.

### 2.2 Đội ngũ CSKH & Quản trị viên (Human Agent)
Nhân viên vận hành nhận thông tin chuyển tiếp từ Chatbot ảo qua hệ thống quản lý ticket.
- **Kịch bản chuyển giao (Handoff)**: Ngay khi Chatbot phát hiện hành vi nguy hiểm (Prompt Injection), sự cố bảo mật (OTP leakage) hoặc giao dịch bị FAILED/PENDING kéo dài, hệ thống lập tức khóa/tạo ticket hỗ trợ độ ưu tiên cao (`HIGH`) gửi tới quản trị viên để kết nối cuộc gọi.

---

## 3. Danh sách Tính năng chính (Functional Requirements)

### F1: Hội thoại thông minh & RAG Pipeline
- Phản hồi tự nhiên bằng tiếng Việt dựa trên nguồn tri thức chính thống được lưu trữ trong Database.
- Tuyệt đối không tự suy diễn các thông số hạn mức, biểu phí hoặc phần trăm nếu tài liệu nguồn không đề cập (Hallucination Control).

### F2: Phân loại ý định (Intent Taxonomy)
Tự động phân loại 14 nhóm ý định chính thức:
- Hạn mức (`LIMIT_INQUIRY`), Biểu phí (`FEE_INQUIRY`), Trạng thái giao dịch (`TRANSACTION_STATUS`), Số dư tài khoản (`BALANCE_INQUIRY`), Khuyến mãi (`PROMOTION_INQUIRY`).
- Sự cố bảo mật (`ACCOUNT_SECURITY`), Báo cáo lừa đảo (`FRAUD_OR_SCAM_REPORT`), Giao dịch thất bại (`FAILED_TRANSACTION`), Yêu cầu gặp người thật (`HUMAN_SUPPORT_REQUEST`).

### F3: Mock Wallet Tools Integration
- Tích hợp gọi API ví giả lập để thực thi các tác vụ: kiểm tra số dư, kiểm tra trạng thái giao dịch theo mã ID, và tính toán biểu phí chính xác.

### F4: Bảo vệ đầu vào & Chặn Prompt Injection
- Tự động quét và phát hiện các mẫu tấn công prompt injection như `"ignore previous instructions"`, `"jailbreak"`, v.v. và thực hiện từ chối phản hồi lập tức.

---

## 4. Các yêu cầu phi chức năng (Non-Functional Requirements)

- **Độ trễ phản hồi (Latency)**: Thời gian phản hồi phân vị 95 (p95 latency) phải nhỏ hơn **2.0 giây** trong điều kiện môi trường local hoặc FAISS fallback.
- **Độ trung thực (Groundedness)**: Tỷ lệ câu trả lời có dẫn nguồn đáng tin cậy đạt tối thiểu **95%** trên bộ dữ liệu kiểm định.
- **Bảo mật**: Tuyệt đối không lưu mật khẩu plaintext, không yêu cầu hay tiết lộ mã OTP đầy đủ của khách hàng trong suốt quá trình trao đổi.
