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
    # 1. Validate request files constraints
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")
        
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Cannot upload more than 10 files in a single request.")

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
        raise HTTPException(status_code=400, detail="Total request payload size exceeds 50MB limit.")

    # 2. Register files and dispatch background processing tasks
    for file_name, file_bytes in file_payloads:
        try:
            # Hash checks, identical file re-upload cleanups, and record insertion
            res = await doc_service.check_and_prepare_upload(file_name, file_bytes)
            results.append(res)
            
            # If successfully inserted as 'processing', launch background extraction & embedding
            if res.status == "processing" and res.doc_id:
                background_tasks.add_task(
                    doc_service.process_document_background,
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

    return UploadResponse(
        success=True,
        message="Documents received. Processing started in the background.",
        data=results
    )


@router.get("/", response_model=List[DocumentListItem])
async def list_documents():
    """Lấy danh sách tất cả tài liệu đã upload, sắp xếp mới nhất trước."""
    docs = await doc_service.list_documents()
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


@router.get("/{doc_id}/status", response_model=DocStatusResponse)
async def get_document_status(doc_id: str):
    doc = await doc_service.get_document_status(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    return DocStatusResponse(
        doc_id=doc["doc_id"],
        file_name=doc["file_name"],
        status=doc["status"],
        chunk_count=doc.get("chunk_count", 0),
        error_message=doc.get("error_message")
    )


@router.get("/{doc_id}/chunks", response_model=List[DocumentChunkItem])
async def get_document_chunks(doc_id: str):
    """Xem danh sách tất cả chunk (đoạn văn bản đã chia nhỏ) của một tài liệu cụ thể."""
    # Kiểm tra tài liệu tồn tại
    doc = await doc_service.get_document_status(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    
    chunks = await doc_service.get_document_chunks(doc_id)
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


@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    """Xóa tài liệu và toàn bộ chunk embedding liên quan."""
    deleted = await doc_service.delete_document(doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found.")
    return {"success": True, "message": f"Tài liệu {doc_id} và toàn bộ chunk đã được xóa thành công."}




