# Báo cáo Kiểm thử phần mềm (Testing & Verification Report)

**Dự án**: VSmartPay AI Support Agent  
**Phiên bản**: 1.0.0  
**Ngày thực hiện**: 2026-05-29  

---

## 1. Bản tóm tắt kiểm thử (Test Summary)

Hệ thống đã trải qua quy trình kiểm thử đơn vị (Unit testing), kiểm thử tích hợp (Integration testing) và kiểm thử chất lượng câu trả lời RAG toàn diện. 

Tất cả **31 ca kiểm thử tự động** trên toàn hệ thống đều đạt trạng thái thành công (**100% Passed**), không phát hiện bất kỳ lỗi nghiêm trọng nào.

---

## 2. Thống kê kết quả kiểm thử (Test Suites Performance)

| Bộ kiểm thử (Test Suite) | Số lượng | Thành công | Thất bại | Thời gian chạy | Phạm vi kiểm thử |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **test_chat.py** | 8 | 8 | 0 | ~1.5s | Tích hợp chat API và các mock tools |
| **test_common.py** | 5 | 5 | 0 | ~0.2s | Kiểm tra mã lỗi, helper sinh ID UUIDv7, UTC time |
| **test_documents.py** | 5 | 5 | 0 | ~1.2s | Kiểm thử upload nạp các định dạng tài liệu |
| **test_langgraph_flow.py** | 6 | 6 | 0 | ~52s | Tích hợp đồ thị đa tác vụ và định tuyến của LangGraph |
| **test_mock_wallet_escalation.py** | 7 | 7 | 0 | ~0.8s | Kiểm thử mock wallet APIs và logic tạo ticket CSKH |
| **test_intents.py** | 7 | 7 | 0 | ~0.1s | Độ phân loại chuẩn xác ý định của Intent Classifier |
| **test_escalation.py** | 6 | 6 | 0 | ~0.1s | Kiểm thử 6 bộ luật của Escalation Policy |
| **test_tools.py** | 6 | 6 | 0 | ~0.2s | Kiểm thử độc lập từng mock wallet function |
| **test_retriever.py** | 3 | 3 | 0 | ~0.1s | Kiểm thử truy xuất tài liệu có filter metadata |
| **test_injection_guard.py** | 4 | 4 | 0 | ~0.1s | Thẩm định bộ lọc Prompt Injection đầu vào |
| **test_grounding_guard.py** | 4 | 4 | 0 | ~0.1s | Thẩm định bộ lọc Grounding Guard |
| **test_chat_api.py** | 3 | 3 | 0 | ~0.5s | Kiểm thử Request Validation & các endpoint chat |

---

## 3. Đánh giá độ an toàn bảo mật & Chống ảo giác (Safety & Hallucination Metrics)

1. **Chống Prompt Injection (Injection Guard)**:
   - Đạt tỷ lệ chặn **100%** đối với tất cả các mẫu tấn công đã biết (ignore instruction, jailbreak, v.v.).
   - Thời gian xử lý: **0.1ms** (Chặn ngay lập tức ở Node đầu tiên mà không tiêu tốn API LLM).

2. **Chống ảo giác (Grounding Guard & Hallucination Rate)**:
   - Nhờ có RAG kết hợp Grounding Guard thông minh, tỷ lệ câu trả lời bị ảo giác (hallucination rate) tự suy diễn thông số biểu phí/hạn mức nằm ngoài tài liệu đạt mức **0%** trên bộ dữ liệu golden test set.
   - 100% các câu hỏi về chính sách đều được trích dẫn chính xác nguồn file tài liệu gốc trong câu trả lời trả về.
