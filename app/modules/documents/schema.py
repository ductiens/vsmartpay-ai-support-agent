from pydantic import BaseModel
from typing import List, Optional

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
