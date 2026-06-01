# Tài liệu Thiết kế Kỹ thuật (Technical Design Document - TDD)

**Dự án**: VSmartPay AI Support Agent  
**Phiên bản**: 1.0.0  

---

## 1. Kiến trúc Hệ thống (System Architecture)

Hệ thống được thiết kế theo mô hình **Đa Tác Vụ Điều Phối bằng Đồ Thị (LangGraph Multi-Agent StateGraph)** chạy trên nền tảng **FastAPI**, lưu trữ dữ liệu tri thức trên **MongoDB Atlas** và hỗ trợ tìm kiếm vector tương đồng qua **Atlas Vector Search** (hoặc **FAISS** fallback cục bộ).

```text
       [ Khách hàng ]
             │ (POST /chat)
             ▼
      [ API Gateway ] ─────── (USE_LANGGRAPH=False) ───────► [ Legacy RAG Flow ]
             │
             │ (USE_LANGGRAPH=True)
             ▼
   [ LangGraph StateGraph ]
     ├── 1. injection_guard_node
     ├── 2. intent_agent_node
     ├── 3. tool_router_node (Mock Wallet Tools)
     ├── 4. rag_agent_node (Atlas Vector Search / FAISS)
     ├── 5. grounding_guard_node
     └── 6. confidence_agent_node ────► [ route_decision ]
                                               │
               ┌───────────────────────────────┼──────────────────────────────┐
               ▼ (Low Confidence/Ungrounded)   ▼ (High-Risk/Escalated)        ▼ (Success)
     [ clarification_agent ]           [ escalation_agent ]             [ final_answer ]
               │                               │                              │
               └───────────────────────────────┴──────────────────────────────┘
                                               │
                                               ▼ (Response JSON)
                                         [ Khách hàng ]
```

---

## 2. Đặc tả cơ sở dữ liệu & MongoDB Atlas Vector Search Index Spec

Dữ liệu tài liệu tri thức được lưu trữ trong collection `knowledge_chunks` của MongoDB.

### 2.1 Cấu trúc Document trong Collection `knowledge_chunks`
```json
{
  "_id": "ObjectId(...)",
  "chunk_id": "chk_limit_01",
  "doc_id": "limits.md",
  "file_name": "limits.md",
  "category": "Hạn mức",
  "content": "Hạn mức giao dịch tối đa qua ví VSmartPay là 50.000.000 VND/ngày...",
  "embedding": [0.012, -0.045, 0.123, "...1536 chiều..."],
  "kb_type": "policy",
  "language": "vi",
  "agent_scope": "limits"
}
```

### 2.2 Đặc tả Vector Search Index trên MongoDB Atlas
Định nghĩa chỉ mục Vector Search (Atlas Search Index JSON config):
```json
{
  "name": "vector_index",
  "type": "vectorSearch",
  "definition": {
    "fields": [
      {
        "type": "vector",
        "path": "embedding",
        "numDimensions": 1536,
        "similarity": "cosine"
      },
      {
        "type": "filter",
        "path": "kb_type"
      },
      {
        "type": "filter",
        "path": "agent_scope"
      }
    ]
  }
}
```
*Lưu ý*: Với môi trường phát triển local không chạy MongoDB Atlas, hệ thống sẽ sử dụng **FAISS FlatIP Index** kết hợp bộ lọc metadata cục bộ bằng `numpy` hoặc tìm kiếm manual fallback trên bộ dữ liệu `knowledge_chunks` để đảm bảo hoạt động độc lập tuyệt đối.

---

## 3. Quy trình nạp tài liệu tự động (Document Ingestion API)

API nạp tài liệu hỗ trợ tải các tài liệu dạng `.md`, `.txt`, `.pdf`, hoặc `.docx` lên để tự động phân tích (parse), chia nhỏ (chunk), tạo embedding qua OpenAI và lưu trữ vào chỉ mục.

### Sơ đồ luồng Ingestion Pipeline:
```text
 [ Admin/User ] ──► [ POST /api/v1/documents/upload ]
                           │
                           ▼
                 [ File Type Detector ]
                 ├── PDF Reader (pypdf)
                 ├── Word Reader (python-docx)
                 └── Plain Text / Markdown
                           │
                           ▼
                 [ Chunking & Cleansing ]
                 (300-500 words/chunk, overlap 50)
                           │
                           ▼
              [ Embedding Generation Service ]
              (OpenAI text-embedding-3-small)
                           │
                           ▼
             [ Database Ingestion Service ]
             (Bulk insert to knowledge_chunks)
```
- API Endpoint: `POST /api/v1/documents/upload`
- Tham số truyền vào: `file: UploadFile`, `category: str`, `kb_type: str`, `agent_scope: str`.
- Output: `{"success": true, "message": "Nạp tài liệu thành công!", "chunks_count": 12}`.
