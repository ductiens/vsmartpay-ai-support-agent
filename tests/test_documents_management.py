"""
Integration tests for Document Management APIs:
- GET /documents/ (list)
- GET /documents/{doc_id}/chunks (view chunks)
- DELETE /documents/{doc_id} (delete)
- POST /documents/{doc_id}/reprocess (reprocess)
"""
import pytest
import io
from unittest.mock import patch, AsyncMock

API_PREFIX = "/api/v1"


@pytest.mark.asyncio
async def test_list_documents_empty(client):
    """Listing documents when none exist should return an empty list."""
    response = await client.get(f"{API_PREFIX}/documents/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_list_documents_after_upload(client):
    """After uploading a document, it should appear in the list."""
    with patch("app.modules.rag.embeddings.EmbeddingService.get_embedding", new_callable=AsyncMock) as mock_emb:
        mock_emb.return_value = [0.01] * 1536

        file_content = b"Tai lieu demo list API cho VSmartPay."
        file_io = io.BytesIO(file_content)

        upload_resp = await client.post(
            f"{API_PREFIX}/documents/upload",
            files={"files": ("list_test.txt", file_io, "text/plain")},
            params={"kb_type": "faq", "category": "ListTest"}
        )
        assert upload_resp.status_code == 200
        doc_id = upload_resp.json()["data"][0]["doc_id"]

        # Now list documents
        list_resp = await client.get(f"{API_PREFIX}/documents/")
        assert list_resp.status_code == 200
        docs = list_resp.json()
        doc_ids = [d["doc_id"] for d in docs]
        assert doc_id in doc_ids

        # Find our document and check fields
        our_doc = next(d for d in docs if d["doc_id"] == doc_id)
        assert our_doc["file_name"] == "list_test.txt"
        assert our_doc["status"] in ["processing", "processed"]


@pytest.mark.asyncio
async def test_view_chunks_after_upload(client):
    """After uploading a text document, its chunks should be viewable."""
    with patch("app.modules.rag.embeddings.EmbeddingService.get_embedding", new_callable=AsyncMock) as mock_emb:
        mock_emb.return_value = [0.01] * 1536

        file_content = b"Noi dung tai lieu de xem chunk. Day la mot doan van ban dai hon de co the chia chunk."
        file_io = io.BytesIO(file_content)

        upload_resp = await client.post(
            f"{API_PREFIX}/documents/upload",
            files={"files": ("chunk_test.txt", file_io, "text/plain")},
            params={"kb_type": "policy", "category": "ChunkTest"}
        )
        assert upload_resp.status_code == 200
        doc_id = upload_resp.json()["data"][0]["doc_id"]

        # Import asyncio to wait for background task
        import asyncio
        await asyncio.sleep(2)

        # View chunks
        chunks_resp = await client.get(f"{API_PREFIX}/documents/{doc_id}/chunks")
        assert chunks_resp.status_code == 200
        chunks = chunks_resp.json()
        assert isinstance(chunks, list)
        assert len(chunks) > 0
        
        # Check chunk structure
        first_chunk = chunks[0]
        assert "chunk_id" in first_chunk
        assert "chunk_index" in first_chunk
        assert "content" in first_chunk
        assert len(first_chunk["content"]) > 0


@pytest.mark.asyncio
async def test_view_chunks_not_found(client):
    """Viewing chunks for a non-existent document should return 404."""
    response = await client.get(f"{API_PREFIX}/documents/nonexistent_doc_id/chunks")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_document(client):
    """After deleting a document, it and its chunks should no longer exist."""
    with patch("app.modules.rag.embeddings.EmbeddingService.get_embedding", new_callable=AsyncMock) as mock_emb:
        mock_emb.return_value = [0.01] * 1536

        file_content = b"Tai lieu se bi xoa de kiem thu."
        file_io = io.BytesIO(file_content)

        upload_resp = await client.post(
            f"{API_PREFIX}/documents/upload",
            files={"files": ("delete_test.txt", file_io, "text/plain")},
            params={"kb_type": "other", "category": "DeleteTest"}
        )
        assert upload_resp.status_code == 200
        doc_id = upload_resp.json()["data"][0]["doc_id"]

        # Verify document exists
        status_resp = await client.get(f"{API_PREFIX}/documents/{doc_id}/status")
        assert status_resp.status_code == 200

        # Delete document
        delete_resp = await client.delete(f"{API_PREFIX}/documents/{doc_id}")
        assert delete_resp.status_code == 200
        assert delete_resp.json()["success"] is True

        # Verify document no longer exists
        status_resp2 = await client.get(f"{API_PREFIX}/documents/{doc_id}/status")
        assert status_resp2.status_code == 404

        # Verify chunks no longer exist
        chunks_resp = await client.get(f"{API_PREFIX}/documents/{doc_id}/chunks")
        assert chunks_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_document_not_found(client):
    """Deleting a non-existent document should return 404."""
    response = await client.delete(f"{API_PREFIX}/documents/nonexistent_doc_id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_reprocess_document(client):
    """After reprocessing, the document should have updated chunks."""
    with patch("app.modules.rag.embeddings.EmbeddingService.get_embedding", new_callable=AsyncMock) as mock_emb:
        mock_emb.return_value = [0.01] * 1536

        file_content = b"Tai lieu de reprocess kiem thu. Noi dung VSmartPay tai lieu huong dan su dung."
        file_io = io.BytesIO(file_content)

        upload_resp = await client.post(
            f"{API_PREFIX}/documents/upload",
            files={"files": ("reprocess_test.txt", file_io, "text/plain")},
            params={"kb_type": "faq", "category": "ReprocessTest"}
        )
        assert upload_resp.status_code == 200
        doc_id = upload_resp.json()["data"][0]["doc_id"]

        # Wait for background processing to complete
        import asyncio
        await asyncio.sleep(2)

        # Reprocess the document
        reprocess_resp = await client.post(f"{API_PREFIX}/documents/{doc_id}/reprocess")
        assert reprocess_resp.status_code == 200
        reprocess_data = reprocess_resp.json()
        assert reprocess_data["doc_id"] == doc_id
        assert reprocess_data["status"] == "processed"
        assert reprocess_data["chunk_count"] > 0


@pytest.mark.asyncio
async def test_reprocess_document_not_found(client):
    """Reprocessing a non-existent document should return 404."""
    response = await client.post(f"{API_PREFIX}/documents/nonexistent_doc_id/reprocess")
    assert response.status_code == 404
