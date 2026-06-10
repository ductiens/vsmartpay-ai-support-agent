from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, Query
from typing import List, Optional
from app.modules.documents.schema import (
    UploadResult, UploadResponse, DocStatusResponse,
    DocumentListItem, DocumentChunkItem
)
from app.modules.documents.service import DocumentService

router = APIRouter(prefix="/documents", tags=["Documents Management"])
doc_service = DocumentService()

@router.post("/upload", response_model=UploadResponse)
async def upload_documents(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    agent_scope: Optional[str] = Query(None, description="Scope target agent for this knowledge chunk"),
    kb_type: str = Query("other", description="Type of knowledge base: faq / policy / product / other"),
    category: str = Query("General", description="Grouping category"),
    language: str = Query("vi", description="Document language: vi / en")
):
    results = await doc_service.handle_batch_upload(
        files, background_tasks, agent_scope, kb_type, category, language
    )
    return UploadResponse(
        success=True,
        message="Documents received. Processing started in the background.",
        data=results
    )


@router.get("/", response_model=List[DocumentListItem])
async def list_documents():
    """Lấy danh sách tất cả tài liệu đã upload, sắp xếp mới nhất trước."""
    return await doc_service.list_documents()


@router.get("/{doc_id}/status", response_model=DocStatusResponse)
async def get_document_status(doc_id: str):
    return await doc_service.get_document_status(doc_id)


@router.get("/{doc_id}/chunks", response_model=List[DocumentChunkItem])
async def get_document_chunks(doc_id: str):
    """Xem danh sách tất cả chunk (đoạn văn bản đã chia nhỏ) của một tài liệu cụ thể."""
    return await doc_service.get_document_chunks(doc_id)


@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    """Xóa tài liệu và toàn bộ chunk embedding liên quan."""
    return await doc_service.delete_document(doc_id)




