from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class UploadResult(BaseModel):
    doc_id: Optional[str] = None
    file_name: str
    status: str  # processing / processed / failed / duplicate
    chunk_count: int = 0
    error_message: Optional[str] = None

class UploadResponse(BaseModel):
    success: bool
    message: str
    data: List[UploadResult]

class DocStatusResponse(BaseModel):
    doc_id: str
    file_name: str
    status: str
    chunk_count: int
    error_message: Optional[str] = None
    cloudinary_url: Optional[str] = None

class DocumentListItem(BaseModel):
    doc_id: str
    file_name: str
    status: str
    chunk_count: int
    error_message: Optional[str] = None
    cloudinary_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class DocumentChunkItem(BaseModel):
    chunk_id: str
    chunk_index: int
    content: str
    page: Optional[int] = None
    heading: Optional[str] = None
    category: Optional[str] = None
    kb_type: Optional[str] = None
    token_count: Optional[int] = None

