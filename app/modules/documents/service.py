import io
import os
import uuid
import hashlib
from typing import List, Dict, Any, Optional
import tiktoken
from pypdf import PdfReader
import docx

from app.config import settings
from app.database import get_db
from app.common.utils import now_utc, generate_id
from app.modules.documents.schema import UploadResult
from app.modules.rag.embeddings import EmbeddingService
from app.modules.rag.vector_store import VectorStoreService

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
        Extract text from file.
        Returns a list of dicts: [{"text": str, "page": int or None, "heading": str or None}]
        """
        ext = os.path.splitext(file_name)[1].lower()
        extracted_pages = []

        if ext == ".txt":
            text = file_bytes.decode("utf-8", errors="ignore")
            extracted_pages.append({"text": text, "page": None, "heading": None})
            
        elif ext == ".md":
            text = file_bytes.decode("utf-8", errors="ignore")
            extracted_pages.append({"text": text, "page": None, "heading": None})
            
        elif ext == ".pdf":
            reader = PdfReader(io.BytesIO(file_bytes))
            for idx, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                extracted_pages.append({
                    "text": page_text,
                    "page": idx + 1,  # 1-based index
                    "heading": None
                })
                
        elif ext == ".docx":
            doc = docx.Document(io.BytesIO(file_bytes))
            text_lines = []
            current_heading = None
            
            for para in doc.paragraphs:
                style_name = para.style.name.lower()
                text = para.text.strip()
                if not text:
                    continue
                    
                if "heading 1" in style_name:
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
                    
            combined_text = "\n\n".join(text_lines)
            extracted_pages.append({
                "text": combined_text,
                "page": None,
                "heading": current_heading
            })
            
        else:
            raise ValueError(f"Unsupported file extension: {ext}")

        return extracted_pages

    def _recursive_split(
        self, 
        text: str, 
        separators: List[str], 
        chunk_size: int = 700, 
        chunk_overlap: int = 100
    ) -> List[str]:
        """
        Recursive character splitting based on tokens count.
        """
        if self._count_tokens(text) <= chunk_size:
            return [text]

        # Find the first separator that exists in the text
        separator = None
        for s in separators:
            if s in text:
                separator = s
                break

        if separator is None:
            # Hard splitting if no separator is found
            words = text.split(" ")
            chunks = []
            current_chunk = []
            
            for word in words:
                current_chunk.append(word)
                if self._count_tokens(" ".join(current_chunk)) > chunk_size:
                    chunks.append(" ".join(current_chunk[:-1]))
                    # Overlap logic
                    current_chunk = current_chunk[-max(1, int(chunk_overlap / 5)):] + [word]
            if current_chunk:
                chunks.append(" ".join(current_chunk))
            return chunks

        # Split text by separator
        splits = text.split(separator)
        final_chunks = []
        current_chunk_parts = []
        
        for split in splits:
            if not split.strip():
                continue
                
            # If current split itself exceeds chunk_size, split it recursively with remaining separators
            if self._count_tokens(split) > chunk_size:
                # Save current built chunk first
                if current_chunk_parts:
                    final_chunks.append(separator.join(current_chunk_parts))
                    current_chunk_parts = []
                
                sub_chunks = self._recursive_split(split, separators[separators.index(separator)+1:], chunk_size, chunk_overlap)
                final_chunks.extend(sub_chunks)
            else:
                # Add to current chunk if it doesn't exceed size
                candidate_chunk = separator.join(current_chunk_parts + [split])
                if self._count_tokens(candidate_chunk) <= chunk_size:
                    current_chunk_parts.append(split)
                else:
                    final_chunks.append(separator.join(current_chunk_parts))
                    # Retain overlap elements
                    current_chunk_parts = [split]
                    
        if current_chunk_parts:
            final_chunks.append(separator.join(current_chunk_parts))

        return final_chunks

    def _chunk_document(
        self, 
        extracted_pages: List[Dict[str, Any]], 
        chunk_size: int = 700, 
        chunk_overlap: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Chunk the normalized pages text using recursive splitter while retaining page/heading structure.
        """
        separators = ["\n# ", "\n## ", "\n### ", "\n#### ", "\n\n", "\n", " ", ""]
        all_chunks = []
        chunk_index = 0

        for page_data in extracted_pages:
            text = page_data["text"]
            page_num = page_data["page"]
            heading = page_data["heading"]

            # Perform recursive character splitting on page/document text
            splits = self._recursive_split(text, separators, chunk_size, chunk_overlap)

            for split in splits:
                if not split.strip():
                    continue
                
                # Detect active heading inside the chunk if not explicitly provided
                active_heading = heading
                if not active_heading:
                    # Find closest preceding markdown heading in this chunk
                    headings = re_find_headings = [
                        line.replace("#", "").strip() 
                        for line in split.split("\n") 
                        if line.strip().startswith("#")
                    ]
                    if headings:
                        active_heading = headings[-1]

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
        Check file size/types, SHA256 hashes for duplicate, 
        and clean up old records for identical file names with different content.
        """
        doc_col = self.documents_collection
        if doc_col is None:
            return UploadResult(file_name=file_name, status="failed", error_message="Database not available")

        # Validate file size (10MB limit)
        if len(file_bytes) > 10 * 1024 * 1024:
            return UploadResult(file_name=file_name, status="failed", error_message="File exceeds 10MB limit")

        # Validate file extension
        ext = os.path.splitext(file_name)[1].lower()
        if ext not in [".pdf", ".docx", ".txt", ".md"]:
            return UploadResult(file_name=file_name, status="failed", error_message="Unsupported file type")

        # Calculate SHA256 Hash
        file_hash = self._compute_sha256(file_bytes)

        # 1. Check duplicate SHA256 Hash
        existing_doc = await doc_col.find_one({"file_hash": file_hash})
        if existing_doc:
            return UploadResult(
                doc_id=existing_doc["doc_id"],
                file_name=file_name,
                status="duplicate",
                chunk_count=existing_doc.get("chunk_count", 0)
            )

        # 2. Check identical filename but different hash -> Re-upload cleanup behavior
        same_name_doc = await doc_col.find_one({"file_name": file_name})
        if same_name_doc:
            old_doc_id = same_name_doc["doc_id"]
            print(f"File name '{file_name}' already exists with different hash. Cleaning up doc_id '{old_doc_id}'...")
            # Delete old chunks
            await self.vector_store.delete_chunks_by_doc_id(old_doc_id)
            # Delete old document record
            await doc_col.delete_one({"doc_id": old_doc_id})

        # Insert placeholder document record as 'processing'
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
        """Retrieve document record by doc_id."""
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
        Background Task: Extracts text, chunks, computes OpenAI embeddings, 
        indexes into MongoDB knowledge_chunks, and updates documents collection.
        """
        doc_col = self.documents_collection
        if doc_col is None:
            return

        try:
            # 1. Extract text
            extracted_pages = self._extract_text(file_name, file_bytes)
            
            # Combine raw text to save in DB for future reprocessing
            raw_text = "\n\n".join([p["text"] for p in extracted_pages])

            # 2. Semantic Structure-aware chunking
            chunks = self._chunk_document(extracted_pages)

            if not chunks:
                raise ValueError("No text could be extracted or chunked from this file.")

            # 3. Generate embeddings and save to MongoDB Atlas Vector Search
            chunk_docs = []
            for item in chunks:
                content = item["content"]
                
                # Prepend heading to the content to preserve heading context for embedding
                contextualized_content = content
                if item["heading"]:
                    contextualized_content = f"Tiêu đề: {item['heading']}\nNội dung: {content}"

                embedding = await self.embedding_service.get_embedding(contextualized_content)
                
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
                    "language": language
                })

            # Save chunks to DB
            await self.vector_store.add_chunks(chunk_docs)

            # 4. Update status to 'processed'
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
            # Update status to 'failed'
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
