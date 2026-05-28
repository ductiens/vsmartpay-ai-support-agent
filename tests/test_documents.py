import pytest
import io
from unittest.mock import patch, AsyncMock
from app.modules.documents.service import DocumentService

@pytest.mark.asyncio
async def test_upload_txt_file_success(client):
    # Mock embedding generation
    with patch("app.modules.rag.embeddings.EmbeddingService.get_embedding", new_callable=AsyncMock) as mock_get_emb:
        mock_get_emb.return_value = [0.01] * 1536
        
        # Prepare mock file content
        file_content = b"Day la tai lieu kiem thu tieng Viet gia lap cho VSmartPay."
        file_io = io.BytesIO(file_content)
        
        # Call API POST /api/v1/documents/upload
        response = await client.post(
            "/api/v1/documents/upload",
            files={"files": ("test_doc.txt", file_io, "text/plain")},
            params={"kb_type": "policy", "category": "KiemThu"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        upload_results = data["data"]
        assert len(upload_results) == 1
        assert upload_results[0]["file_name"] == "test_doc.txt"
        assert upload_results[0]["status"] == "processing"
        assert upload_results[0]["doc_id"] is not None
        
        doc_id = upload_results[0]["doc_id"]
        
        # Check Polling GET /api/v1/documents/{doc_id}/status
        status_response = await client.get(f"/api/v1/documents/{doc_id}/status")
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["doc_id"] == doc_id
        assert status_data["file_name"] == "test_doc.txt"
        assert status_data["status"] in ["processing", "processed"]


@pytest.mark.asyncio
async def test_upload_duplicate_hash(client):
    with patch("app.modules.rag.embeddings.EmbeddingService.get_embedding", new_callable=AsyncMock) as mock_get_emb:
        mock_get_emb.return_value = [0.01] * 1536
        
        file_content = b"Tep tin trung lap hash."
        
        # Upload first time
        file_io1 = io.BytesIO(file_content)
        response1 = await client.post(
            "/api/v1/documents/upload",
            files={"files": ("file1.txt", file_io1, "text/plain")}
        )
        doc_id1 = response1.json()["data"][0]["doc_id"]
        
        # Upload second time (same content, same hash)
        file_io2 = io.BytesIO(file_content)
        response2 = await client.post(
            "/api/v1/documents/upload",
            files={"files": ("file2.txt", file_io2, "text/plain")}
        )
        
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["data"][0]["status"] == "duplicate"
        assert data2["data"][0]["doc_id"] == doc_id1


@pytest.mark.asyncio
async def test_reupload_different_hash_replaces_old_file(client):
    with patch("app.modules.rag.embeddings.EmbeddingService.get_embedding", new_callable=AsyncMock) as mock_get_emb:
        mock_get_emb.return_value = [0.01] * 1536
        
        filename = "reupload_test.txt"
        
        # Upload file first time
        file_io1 = io.BytesIO(b"Noi dung goc ban dau.")
        response1 = await client.post(
            "/api/v1/documents/upload",
            files={"files": (filename, file_io1, "text/plain")}
        )
        doc_id1 = response1.json()["data"][0]["doc_id"]
        
        # Verify first document status exists
        status1 = await client.get(f"/api/v1/documents/{doc_id1}/status")
        assert status1.status_code == 200
        
        # Upload file second time (same filename, different content/hash)
        file_io2 = io.BytesIO(b"Noi dung moi da duoc thay doi.")
        response2 = await client.post(
            "/api/v1/documents/upload",
            files={"files": (filename, file_io2, "text/plain")}
        )
        
        assert response2.status_code == 200
        data2 = response2.json()
        doc_id2 = data2["data"][0]["doc_id"]
        
        assert doc_id2 != doc_id1
        assert data2["data"][0]["status"] == "processing"
        
        # Polling old doc_id should return 404 since it got deleted from the database
        status_old = await client.get(f"/api/v1/documents/{doc_id1}/status")
        assert status_old.status_code == 404


@pytest.mark.asyncio
async def test_upload_invalid_file_extension(client):
    file_content = b"Image binary mock."
    file_io = io.BytesIO(file_content)
    
    # Uploading a .png which is not in supported [PDF, DOCX, TXT, MD] list
    response = await client.post(
        "/api/v1/documents/upload",
        files={"files": ("photo.png", file_io, "image/png")}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["data"][0]["status"] == "failed"
    assert "Unsupported file type" in data["data"][0]["error_message"]


@pytest.mark.asyncio
async def test_upload_file_exceeding_size_limit(client):
    # Creating large mock byte string exceeding 10MB limit (11MB)
    large_content = b"A" * (11 * 1024 * 1024)
    file_io = io.BytesIO(large_content)
    
    response = await client.post(
        "/api/v1/documents/upload",
        files={"files": ("huge_file.txt", file_io, "text/plain")}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["data"][0]["status"] == "failed"
    assert "File exceeds 10MB limit" in data["data"][0]["error_message"]
