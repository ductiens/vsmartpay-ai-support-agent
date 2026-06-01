import io
import os
import uuid
import hashlib
import re
import unicodedata
import zipfile
from collections import Counter
from typing import List, Dict, Any, Optional
import tiktoken
import docx

from app.config import settings
from app.database import get_db
from app.common.utils import now_utc, generate_id
from app.modules.documents.schema import UploadResult
from app.modules.rag.embeddings import EmbeddingService
from app.modules.rag.vector_store import VectorStoreService


def detect_file_type(file_name: str, file_bytes: bytes, content_type: Optional[str] = None) -> str:
    """
    Phát hiện loại file dựa trên extension, MIME type, và magic bytes.
    Hỗ trợ giai đoạn đầu: PDF, DOCX, TXT, MD.
    Trả về một trong các chuỗi: 'pdf', 'docx', 'txt', 'md' hoặc raise ValueError.
    """
    ext = os.path.splitext(file_name)[1].lower()
    magic = file_bytes[:4]
    
    # 1. Phát hiện PDF
    if magic.startswith(b'%PDF') or content_type == "application/pdf" or ext == ".pdf":
        if magic.startswith(b'%PDF') or ext == ".pdf":
            return "pdf"
            
    # 2. Phát hiện DOCX (docx là file ZIP có magic bytes PK\x03\x04)
    if magic.startswith(b'PK\x03\x04') or content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or ext == ".docx":
        if magic.startswith(b'PK\x03\x04') or ext == ".docx":
            # Kiểm tra xem có thực sự là file docx bằng cách check file word/document.xml bên trong
            try:
                with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
                    if "word/document.xml" in zf.namelist():
                        return "docx"
            except Exception:
                pass
            if ext == ".docx":
                return "docx"
                
    # 3. Phát hiện MD
    if ext == ".md" or content_type in ["text/markdown", "text/x-markdown"]:
        return "md"
        
    # 4. Phát hiện TXT
    if ext == ".txt" or content_type == "text/plain":
        return "txt"
        
    raise ValueError("Unsupported file type")


def clean_text(text: str) -> str:
    """
    Làm sạch văn bản theo các bước:
    - Chuẩn hóa Unicode tiếng Việt về NFC.
    - Xóa số trang.
    - Xóa dòng trống thừa (giữ tối đa 1 dòng trống liên tiếp).
    """
    if not text:
        return ""
        
    # 1. Chuẩn hóa NFC
    text = unicodedata.normalize('NFC', text)
    
    # 2. Xóa số trang (ví dụ: "Trang 1", "Page 1 of 5", "Trang 1 / 10", v.v.)
    text = re.sub(r'(?i)\b(trang|page)\s*\d+(\s*of\s*\d+|\s*/\s*\d+)?\b', '', text)
    
    # Xóa các dòng chỉ chứa chữ số đơn lẻ (ví dụ số trang đứng độc lập ở đầu/cuối trang)
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        if re.match(r'^\s*\d+\s*$', line):
            continue
        cleaned_lines.append(line)
    text = "\n".join(cleaned_lines)
    
    # 3. Xóa dòng trống thừa (giữ tối đa 1 dòng trống liên tiếp)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()


def remove_repeated_headers_footers(pages_text: List[str]) -> List[str]:
    """
    Tự động phát hiện và loại bỏ các header/footer lặp lại trên nhiều trang.
    Dòng được coi là header/footer lặp lại nếu xuất hiện ở đầu/cuối trang
    trong ít nhất 3 trang và chiếm >= 30% tổng số trang.
    """
    n_pages = len(pages_text)
    if n_pages < 3:
        return pages_text
        
    first_lines = []
    last_lines = []
    
    for page in pages_text:
        lines = [line.strip() for line in page.split("\n") if line.strip()]
        if lines:
            first_lines.append(lines[0])
            if len(lines) > 1:
                last_lines.append(lines[-1])
                
    threshold = max(3, int(n_pages * 0.3))
    
    first_counts = Counter(first_lines)
    last_counts = Counter(last_lines)
    
    headers_to_remove = {line for line, count in first_counts.items() if count >= threshold}
    footers_to_remove = {line for line, count in last_counts.items() if count >= threshold}
    
    cleaned_pages = []
    for page in pages_text:
        lines = page.split("\n")
        new_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped in headers_to_remove or stripped in footers_to_remove:
                continue
            new_lines.append(line)
        cleaned_pages.append("\n".join(new_lines))
        
    return cleaned_pages


class DocumentService:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStoreService()
        self._tokenizer = tiktoken.get_encoding("cl100k_base")

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

    def _count_tokens(self, text: str) -> int:
        return len(self._tokenizer.encode(text))

    def _compute_sha256(self, file_bytes: bytes) -> str:
        return hashlib.sha256(file_bytes).hexdigest()

    def _extract_text(self, file_name: str, file_bytes: bytes) -> List[Dict[str, Any]]:
        """
        Trích xuất nội dung văn bản từ các file được hỗ trợ (PDF, DOCX, TXT, MD).
        Đồng thời phát hiện và chặn file PDF scan nếu > 50% số trang có ít hơn 100 ký tự.
        """
        file_type = detect_file_type(file_name, file_bytes)
        extracted_pages = []

        if file_type == "txt" or file_type == "md":
            text = file_bytes.decode("utf-8", errors="ignore")
            cleaned_text_content = clean_text(text)
            extracted_pages.append({
                "text": cleaned_text_content,
                "page": None,
                "heading": None
            })
            
        elif file_type == "pdf":
            import fitz
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            n_pages = len(doc)
            
            pages_raw = []
            scanned_pages_count = 0
            
            for idx in range(n_pages):
                page = doc.load_page(idx)
                page_text = page.get_text() or ""
                # Đếm số ký tự (bỏ qua khoảng trắng)
                if len(page_text.strip()) < 100:
                    scanned_pages_count += 1
                pages_raw.append(page_text)
                
            # Chặn nếu quá nửa số trang có ít hơn 100 ký tự (PDF Scan)
            if n_pages > 0 and (scanned_pages_count / n_pages) > 0.5:
                raise ValueError("file scan chưa được hỗ trợ")
                
            # Tự động loại bỏ Header & Footer lặp lại giữa các trang
            cleaned_pages = remove_repeated_headers_footers(pages_raw)
            
            for idx, page_text in enumerate(cleaned_pages):
                cleaned_page_text = clean_text(page_text)
                extracted_pages.append({
                    "text": cleaned_page_text,
                    "page": idx + 1,
                    "heading": None
                })
                
        elif file_type == "docx":
            doc = docx.Document(io.BytesIO(file_bytes))
            
            def iter_block_items(parent):
                from docx.document import Document
                from docx.oxml.table import CT_Tbl
                from docx.oxml.text.paragraph import CT_P
                from docx.table import Table
                from docx.text.paragraph import Paragraph

                if isinstance(parent, Document):
                    parent_elm = parent.element.body
                else:
                    parent_elm = parent._element

                for child in parent_elm.iterchildren():
                    if isinstance(child, CT_P):
                        yield Paragraph(child, parent)
                    elif isinstance(child, CT_Tbl):
                        yield Table(child, parent)

            def format_table_to_markdown(table) -> str:
                rows = []
                for row in table.rows:
                    cols = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                    rows.append(cols)
                if not rows:
                    return ""
                
                header = rows[0]
                markdown_lines = []
                markdown_lines.append("| " + " | ".join(header) + " |")
                markdown_lines.append("| " + " | ".join(["---"] * len(header)) + " |")
                for row in rows[1:]:
                    if len(row) < len(header):
                        row.extend([""] * (len(header) - len(row)))
                    elif len(row) > len(header):
                        row = row[:len(header)]
                    markdown_lines.append("| " + " | ".join(row) + " |")
                    
                return "\n".join(markdown_lines)

            text_lines = []
            current_heading = None
            
            for item in iter_block_items(doc):
                if isinstance(item, docx.text.paragraph.Paragraph):
                    style_name = item.style.name.lower() if (item.style and item.style.name) else ""
                    text = item.text.strip()
                    if not text:
                        continue
                        
                    if style_name and "heading 1" in style_name:
                        current_heading = text
                        text_lines.append(f"# {text}")
                    elif "heading 2" in style_name:
                        current_heading = text
                        text_lines.append(f"## {text}")
                    elif "heading 3" in style_name:
                        current_heading = text
                        text_lines.append(f"### {text}")
                    else:
                        text_lines.append(text)
                elif isinstance(item, docx.table.Table):
                    table_md = format_table_to_markdown(item)
                    if table_md:
                        text_lines.append(table_md)
                        
            combined_text = "\n\n".join(text_lines)
            cleaned_combined_text = clean_text(combined_text)
            
            extracted_pages.append({
                "text": cleaned_combined_text,
                "page": None,
                "heading": current_heading
            })
            
        else:
            raise ValueError("Unsupported file type")

        return extracted_pages

    def _chunk_document(
        self, 
        extracted_pages: List[Dict[str, Any]], 
        chunk_size: Optional[int] = None, 
        chunk_overlap: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Chia nhỏ tài liệu sử dụng MarkdownHeaderTextSplitter và RecursiveCharacterTextSplitter.
        Đo lường dung lượng bằng token của mô hình cl100k_base qua tiktoken.
        """
        if chunk_size is None:
            chunk_size = getattr(settings, "CHUNK_SIZE", 800)
        if chunk_overlap is None:
            chunk_overlap = getattr(settings, "CHUNK_OVERLAP", 100)
            
        from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
        
        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
            ("####", "Header 4"),
        ]
        
        recursive_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=self._count_tokens,
            separators=["\n\n", "\n", " ", ""]
        )
        
        all_chunks = []
        chunk_index = 0
        
        for page_data in extracted_pages:
            text = page_data["text"]
            page_num = page_data["page"]
            heading = page_data["heading"]
            
            # Kiểm tra nếu trang có chứa tiêu đề Markdown
            has_markdown_headers = bool(re.search(r'^#+\s+', text, re.MULTILINE))
            
            if has_markdown_headers:
                header_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
                header_chunks = header_splitter.split_text(text)
                
                for hc in header_chunks:
                    active_heading = heading
                    for h_level in ["Header 4", "Header 3", "Header 2", "Header 1"]:
                        if h_level in hc.metadata:
                            active_heading = hc.metadata[h_level]
                            break
                            
                    # Nếu chunk sau khi tách vẫn quá lớn, tiếp tục dùng Recursive
                    if self._count_tokens(hc.page_content) > chunk_size:
                        sub_splits = recursive_splitter.split_text(hc.page_content)
                        for sub_split in sub_splits:
                            all_chunks.append({
                                "chunk_index": chunk_index,
                                "content": sub_split.strip(),
                                "page": page_num,
                                "heading": active_heading
                            })
                            chunk_index += 1
                    else:
                        all_chunks.append({
                            "chunk_index": chunk_index,
                            "content": hc.page_content.strip(),
                            "page": page_num,
                            "heading": active_heading
                        })
                        chunk_index += 1
            else:
                # Text thường, chia trực tiếp qua Recursive splitter
                splits = recursive_splitter.split_text(text)
                for split in splits:
                    if not split.strip():
                        continue
                    
                    active_heading = heading
                    if not active_heading:
                        headings_in_split = [
                            line.replace("#", "").strip() 
                            for line in split.split("\n") 
                            if line.strip().startswith("#")
                        ]
                        if headings_in_split:
                            active_heading = headings_in_split[-1]
                            
                    all_chunks.append({
                        "chunk_index": chunk_index,
                        "content": split.strip(),
                        "page": page_num,
                        "heading": active_heading
                    })
                    chunk_index += 1
                    
        return all_chunks

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

    async def get_document_status(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Lấy thông tin tài liệu theo doc_id."""
        doc_col = self.documents_collection
        if doc_col is not None:
            return await doc_col.find_one({"doc_id": doc_id})
        return None

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
            extracted_pages = self._extract_text(file_name, file_bytes)
            raw_text = "\n\n".join([p["text"] for p in extracted_pages])

            # 2. Chia chunk kết hợp cấu trúc
            chunks = self._chunk_document(extracted_pages)
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
                    "file_name": file_name,
                    "page": item["page"],
                    "heading": item["heading"],
                    "agent_scope": agent_scope,
                    "kb_type": kb_type,
                    "category": category,
                    "language": language,
                    "token_count": self._count_tokens(content),
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
