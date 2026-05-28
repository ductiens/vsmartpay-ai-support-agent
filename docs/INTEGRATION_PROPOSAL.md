# Integration Proposal - Chatbot Support Agent

## 1. Phương án tích hợp RAG & Vector Database
- Sử dụng FAISS cục bộ lưu trữ chỉ mục vector cho tài liệu tri thức (FAQ, hạn mức, biểu phí).
- Tích hợp pipeline tự động cập nhật và phân tích cú pháp dữ liệu raw sang processed hàng ngày hoặc mỗi khi có cập nhật tài liệu mới.

## 2. Phương án tích hợp LangGraph (Phase tiếp theo)
- Sử dụng mô hình đa tác nhân (Multi-Agent) của LangGraph để phân tách nhiệm vụ của Chatbot thành các Nodes độc lập:
  - **Node Phân Loại Ý Định (Classifier Node)**
  - **Node Tra Cứu Tri Thức (RAG Node)**
  - **Node Gọi Công Cụ Tài Chính (Tool Execution Node)**
  - **Node Xử Lý Chuyển Tiếp (Escalation Node)**
- Kết nối các Nodes qua các cạnh điều kiện (Conditional Edges) để điều hướng hội thoại linh hoạt, lưu giữ state thống nhất.
