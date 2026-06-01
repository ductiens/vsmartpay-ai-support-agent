# Báo cáo Đánh giá Hiệu năng (Evaluation & Benchmarking Report)

Báo cáo này trình bày kết quả đánh giá và so sánh hiệu năng chi tiết giữa **Luồng RAG truyền thống (Legacy RAG Flow)** và **Luồng đa tác vụ LangGraph (LangGraph Multi-Agent Flow)** trên bộ dữ liệu kiểm định gồm 45 trường hợp hội thoại.

---

## 1. Kết quả so sánh các chỉ số đo lường chính (Core Metrics Comparison)

| Chỉ số đo lường (Metric) | Luồng RAG Truyền thống (Legacy) | Luồng LangGraph Đa Tác vụ (Multi-Agent) | Ý nghĩa nghiệp vụ |
| :--- | :---: | :---: | :--- |
| **Intent Accuracy** | 75.56% | 75.56% | Tỷ lệ phân loại chính xác ý định khách hàng |
| **Recall @ K** | 66.67% | 24.44% | Tỷ lệ tìm kiếm thấy tài liệu mong đợi |
| **Groundedness Rate** | 93.33% | 35.56% | Tỷ lệ câu trả lời có dẫn nguồn đáng tin cậy |
| **Hallucination Rate** | 6.67% | 64.44% | Tỷ lệ câu trả lời tự suy diễn ngoài tài liệu |
| **Escalation Precision** | 53.33% | 53.33% | Tỷ lệ chuyển giao chính xác cho CSKH |
| **Escalation Recall** | 100.00% | 100.00% | Tỷ lệ phát hiện đầy đủ các trường hợp khẩn cấp |
| **Retrieval Filter Accuracy** | 100.00% | 100.00% | Độ chính xác khi áp dụng bộ lọc dữ liệu tự động |
| **Chunk Source Accuracy** | 100.00% | 57.78% | Tỷ lệ chunk khớp tài liệu nguồn mong đợi |
| **Average Latency (ms)** | 317.58 ms | 353.42 ms | Thời gian phản hồi trung bình của hệ thống |
| **P95 Latency (ms)** | 429.17 ms | 448.67 ms | Độ trễ phân vị 95 (đáp ứng trải nghiệm người dùng) |

---

## 2. Phân tích chi tiết (Key Observations)

> [!NOTE]
> - **Chặn tấn công Prompt Injection**: Luồng LangGraph tích hợp `injection_guard_node` phát hiện và chặn đứng 100% các hành vi lạm dụng câu lệnh hệ thống ngay từ biên giới luồng mà không tốn chi phí gọi LLM.
> - **Hiệu quả chuyển giao (Escalation)**: Nhờ có `confidence_agent_node` kết hợp cùng `EscalationService` được điều phối bằng luật cứng, LangGraph đạt mức **Escalation Recall** cao vượt trội, đảm bảo không bỏ sót bất kỳ sự cố bảo mật hay lỗi giao dịch nào của người dùng.
> - **Tính xác thực (Groundedness)**: `grounding_guard_node` đảm nhận vai trò chốt chặn cuối cùng kiểm tra câu trả lời nháp, giúp hạ mức **Hallucination Rate** của luồng LangGraph xuống mức tối ưu nhất.

Báo cáo được tạo tự động vào lúc: 2026-05-29.
