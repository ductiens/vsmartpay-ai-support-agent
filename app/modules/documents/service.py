import hashlib
from typing import List, Dict, Any, Optional

from app.config import settings
from app.database import get_db
from app.common.utils import now_utc, generate_id
from app.modules.documents.schema import UploadResult
from app.modules.rag.embeddings import EmbeddingService
from app.modules.rag.vector_store import VectorStoreService

from app.modules.documents.parser import detect_file_type, DocumentParser
from app.modules.documents.chunker import DocumentChunker


class DocumentService:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStoreService()
        self.parser = DocumentParser()
        self.chunker = DocumentChunker()

    @property
    def documents_collection(self):
        db = get_db()
        if db is not None:
            return db["documents"]
        return None

    @property
    def chunks_collection(self):
        db = get_db()
        if db is not None:
            return db["knowledge_chunks"]
        return None

    def _compute_sha256(self, file_bytes: bytes) -> str:
        return hashlib.sha256(file_bytes).hexdigest()

    async def check_and_prepare_upload(self, file_name: str, file_bytes: bytes) -> UploadResult:
        """
        Kiểm tra kích thước, loại file và hash trùng lặp.
        Nếu trùng tên nhưng khác nội dung, tiến hành xóa bản ghi cũ trước khi upload.
        """
        doc_col = self.documents_collection
        if doc_col is None:
            return UploadResult(file_name=file_name, status="failed", error_message="Database not available")

        # Giới hạn kích thước file 10MB
        if len(file_bytes) > 10 * 1024 * 1024:
            return UploadResult(file_name=file_name, status="failed", error_message="File exceeds 10MB limit")

        # Kiểm tra tính hợp lệ của file (MIME/magic/extension)
        try:
            detect_file_type(file_name, file_bytes)
        except ValueError:
            return UploadResult(file_name=file_name, status="failed", error_message="Unsupported file type")

        # Tính toán SHA256 Hash
        file_hash = self._compute_sha256(file_bytes)

        # 1. Tránh upload trùng lặp hoàn toàn
        existing_doc = await doc_col.find_one({"file_hash": file_hash})
        if existing_doc:
            return UploadResult(
                doc_id=existing_doc["doc_id"],
                file_name=file_name,
                status="duplicate",
                chunk_count=existing_doc.get("chunk_count", 0)
            )

        # 2. Xử lý re-upload: Trùng tên nhưng khác nội dung
        same_name_doc = await doc_col.find_one({"file_name": file_name})
        if same_name_doc:
            old_doc_id = same_name_doc["doc_id"]
            print(f"File name '{file_name}' already exists with different hash. Cleaning up doc_id '{old_doc_id}'...")
            await self.vector_store.delete_chunks_by_doc_id(old_doc_id)
            await doc_col.delete_one({"doc_id": old_doc_id})

        # Lưu bản ghi placeholder
        doc_id = generate_id()
        utc_now = now_utc()
        
        doc_doc = {
            "doc_id": doc_id,
            "file_name": file_name,
            "file_hash": file_hash,
            "status": "processing",
            "raw_text": "",
            "chunk_count": 0,
            "error_message": None,
            "uploaded_by": "system",
            "created_at": utc_now,
            "updated_at": utc_now
        }
        await doc_col.insert_one(doc_doc)

        return UploadResult(doc_id=doc_id, file_name=file_name, status="processing")

    async def get_document_status(self, doc_id: str):
        from app.modules.documents.schema import DocStatusResponse
        from app.common.exceptions import NotFoundException
        doc_col = self.documents_collection
        if doc_col is not None:
            doc = await doc_col.find_one({"doc_id": doc_id}, {"_id": 0})
            if doc:
                return DocStatusResponse(
                    doc_id=doc["doc_id"],
                    file_name=doc["file_name"],
                    status=doc["status"],
                    chunk_count=doc.get("chunk_count", 0),
                    error_message=doc.get("error_message")
                )
        raise NotFoundException(message="Document not found.")

    async def list_documents(self):
        """Lấy danh sách tất cả tài liệu, sắp xếp mới nhất trước."""
        from app.modules.documents.schema import DocumentListItem
        doc_col = self.documents_collection
        if doc_col is None:
            return []
        cursor = doc_col.find({}, {"_id": 0, "raw_text": 0}).sort("created_at", -1)
        docs = await cursor.to_list(length=200)
        return [
            DocumentListItem(
                doc_id=d["doc_id"],
                file_name=d["file_name"],
                status=d["status"],
                chunk_count=d.get("chunk_count", 0),
                error_message=d.get("error_message"),
                created_at=d.get("created_at"),
                updated_at=d.get("updated_at")
            ) for d in docs
        ]

    async def delete_document(self, doc_id: str):
        """
        Xóa tài liệu và tất cả các chunk embedding liên quan.
        Raise HTTPException 404 nếu tài liệu không tồn tại.
        """
        from app.common.exceptions import InternalServerException, NotFoundException
        doc_col = self.documents_collection
        if doc_col is None:
            raise InternalServerException(message="Database not configured.")
        
        doc = await doc_col.find_one({"doc_id": doc_id})
        if not doc:
            raise NotFoundException(message="Document not found.")
        
        # Xóa tất cả chunk embeddings thuộc về tài liệu này
        await self.vector_store.delete_chunks_by_doc_id(doc_id)
        # Xóa bản ghi tài liệu
        await doc_col.delete_one({"doc_id": doc_id})
        return {"success": True, "message": f"Tài liệu {doc_id} và toàn bộ chunk đã được xóa thành công."}

    async def get_document_chunks(self, doc_id: str):
        """Lấy danh sách tất cả chunk thuộc một tài liệu cụ thể."""
        from app.modules.documents.schema import DocumentChunkItem
        from app.common.exceptions import InternalServerException, NotFoundException
        
        # Check if doc exists
        doc_col = self.documents_collection
        if doc_col is None:
            raise InternalServerException(message="Database not configured.")
            
        doc = await doc_col.find_one({"doc_id": doc_id})
        if not doc:
            raise NotFoundException(message="Document not found.")
            
        chunks_col = self.chunks_collection
        if chunks_col is None:
            return []
            
        cursor = chunks_col.find(
            {"doc_id": doc_id},
            {"_id": 0, "embedding": 0}  # Loại bỏ embedding vector (quá lớn) khỏi response
        ).sort("chunk_index", 1)
        
        chunks = await cursor.to_list(length=500)
        return [
            DocumentChunkItem(
                chunk_id=c.get("chunk_id", ""),
                chunk_index=c.get("chunk_index", 0),
                content=c.get("content", ""),
                page=c.get("page"),
                heading=c.get("heading"),
                category=c.get("category"),
                kb_type=c.get("kb_type"),
                token_count=c.get("token_count")
            ) for c in chunks
        ]

    async def handle_batch_upload(self, files, background_tasks, agent_scope, kb_type, category, language):
        from app.common.exceptions import BadRequestException
        if not files:
            raise BadRequestException(message="No files uploaded.")
            
        if len(files) > 10:
            raise BadRequestException(message="Cannot upload more than 10 files in a single request.")

        # Calculate total size and pre-read files
        total_size = 0
        file_payloads = []
        results = []

        for file in files:
            file_bytes = await file.read()
            file_size = len(file_bytes)
            total_size += file_size
            
            # Max 10MB per file
            if file_size > 10 * 1024 * 1024:
                results.append(UploadResult(
                    file_name=file.filename or "unknown",
                    status="failed",
                    error_message="File exceeds 10MB limit."
                ))
                continue

            file_payloads.append((file.filename, file_bytes))

        # Max 50MB total per request
        if total_size > 50 * 1024 * 1024:
            raise BadRequestException(message="Total request payload size exceeds 50MB limit.")

        # 2. Register files and dispatch background processing tasks
        for file_name, file_bytes in file_payloads:
            try:
                # Hash checks, identical file re-upload cleanups, and record insertion
                res = await self.check_and_prepare_upload(file_name, file_bytes)
                results.append(res)
                
                # If successfully inserted as 'processing', launch background extraction & embedding
                if res.status == "processing" and res.doc_id:
                    background_tasks.add_task(
                        self.process_document_background,
                        doc_id=res.doc_id,
                        file_name=file_name,
                        file_bytes=file_bytes,
                        agent_scope=agent_scope,
                        kb_type=kb_type,
                        category=category,
                        language=language
                    )
            except Exception as e:
                results.append(UploadResult(
                    file_name=file_name,
                    status="failed",
                    error_message=str(e)
                ))

        return results



    async def process_document_background(
        self, 
        doc_id: str, 
        file_name: str, 
        file_bytes: bytes,
        agent_scope: Optional[str] = None,
        kb_type: str = "other",
        category: str = "General",
        language: str = "vi"
    ):
        """
        Background Task: Trích xuất, làm sạch, chia chunk, tạo embedding và lưu vào MongoDB Vector Store.
        """
        doc_col = self.documents_collection
        if doc_col is None:
            return

        try:
            # 1. Trích xuất văn bản
            extracted_pages = self.parser.extract_text(file_name, file_bytes)
            raw_text = "\n\n".join([p["text"] for p in extracted_pages])

            # 2. Chia chunk kết hợp cấu trúc
            chunks = self.chunker.chunk_document(extracted_pages)
            if not chunks:
                raise ValueError("No text could be extracted or chunked from this file.")

            # 3. Tạo embedding và tạo danh sách chunk hoàn chỉnh theo Schema Metadata tiêu chuẩn
            chunk_docs = []
            for item in chunks:
                content = item["content"]
                
                # Bổ sung tiêu đề vào ngữ cảnh embedding để tăng độ khớp tìm kiếm ngữ nghĩa
                contextualized_content = content
                if item["heading"]:
                    contextualized_content = f"Tiêu đề: {item['heading']}\nNội dung: {content}"

                embedding = await self.embedding_service.get_embedding(contextualized_content)
                utc_now = now_utc()
                
                chunk_docs.append({
                    "chunk_id": generate_id(),
                    "doc_id": doc_id,
                    "chunk_index": item["chunk_index"],
                    "content": content,
                    "embedding": embedding,
                    "embedding_model": settings.EMBEDDING_MODEL,
                    "chunk_size": getattr(settings, "CHUNK_SIZE", 800),
                    "chunk_overlap": getattr(settings, "CHUNK_OVERLAP", 100),
                    "file_name": file_name,
                    "page": item["page"],
                    "heading": item["heading"],
                    "agent_scope": agent_scope,
                    "kb_type": kb_type,
                    "category": category,
                    "language": language,
                    "token_count": self.chunker.count_tokens(content),
                    "created_at": utc_now,
                    "updated_at": utc_now
                })

            # Lưu các chunk vào DB
            await self.vector_store.add_chunks(chunk_docs)

            # 4. Cập nhật trạng thái hoàn thành
            utc_now = now_utc()
            await doc_col.update_one(
                {"doc_id": doc_id},
                {
                    "$set": {
                        "status": "processed",
                        "raw_text": raw_text,
                        "chunk_count": len(chunks),
                        "updated_at": utc_now
                    }
                }
            )
            print(f"Background Ingestion succeeded for doc_id '{doc_id}' with {len(chunks)} chunks.")

        except Exception as e:
            # Ghi nhận trạng thái thất bại
            utc_now = now_utc()
            await doc_col.update_one(
                {"doc_id": doc_id},
                {
                    "$set": {
                        "status": "failed",
                        "error_message": str(e),
                        "updated_at": utc_now
                    }
                }
            )
            print(f"Background Ingestion failed for doc_id '{doc_id}': {e}")
