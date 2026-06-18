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
        assert status_data["data"]["doc_id"] == doc_id
        assert status_data["data"]["file_name"] == "test_doc.txt"
        assert status_data["data"]["status"] in ["processing", "processed"]


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


def test_detect_file_type_helper():
    from app.modules.documents.service import detect_file_type
    
    # 1. Test PDF
    assert detect_file_type("document.pdf", b"%PDF-1.4\ncontent") == "pdf"
    assert detect_file_type("document.pdf", b"random_bytes") == "pdf"
    
    # 2. Test MD & TXT
    assert detect_file_type("notes.md", b"# Markdown text") == "md"
    assert detect_file_type("notes.txt", b"Plain text") == "txt"
    
    # 3. Test unsupported
    with pytest.raises(ValueError, match="Unsupported file type"):
        detect_file_type("photo.png", b"\x89PNG\r\n\x1a\n")


def test_clean_text_helper():
    from app.modules.documents.cleaner import clean_text
    
    # Test Vietnamese Unicode NFC normalization
    # "Hòa" can be written as H-o-a-` (decomposed) or Hoa` (composed NFC)
    decomposed = "Ho\u0300a Bi\u0300nh"
    cleaned = clean_text(decomposed)
    import unicodedata
    assert unicodedata.is_normalized("NFC", cleaned)
    
    # Test page numbers removal
    text_with_page = "Doanh thu quy 1.\nTrang 5\nDoanh thu quy 2.\nPage 10 of 20\nTrang 2 / 10\n15"
    cleaned_page = clean_text(text_with_page)
    assert "Trang 5" not in cleaned_page
    assert "Page 10 of 20" not in cleaned_page
    assert "Trang 2 / 10" not in cleaned_page
    assert "15" not in cleaned_page.split("\n")
    
    # Test empty lines removal
    text_with_empty_lines = "Line 1\n\n\n\nLine 2"
    cleaned_empty = clean_text(text_with_empty_lines)
    assert "\n\n\n" not in cleaned_empty
    assert "Line 1\n\nLine 2" == cleaned_empty


def test_remove_repeated_headers_footers_helper():
    from app.modules.documents.cleaner import remove_repeated_headers_footers
    
    pages = [
        "Chinh sach VSmartPay\nNoi dung trang 1\nFooter VSmartPay 2026",
        "Chinh sach VSmartPay\nNoi dung trang 2\nFooter VSmartPay 2026",
        "Chinh sach VSmartPay\nNoi dung trang 3\nFooter VSmartPay 2026",
        "Chinh sach VSmartPay\nNoi dung trang 4\nFooter khac",
    ]
    
    cleaned = remove_repeated_headers_footers(pages)
    # "Chinh sach VSmartPay" appears in 4/4 pages (>= 3 pages and >= 30%) -> should be removed
    # "Footer VSmartPay 2026" appears in 3/4 pages (>= 3 pages and >= 30%) -> should be removed
    # "Footer khac" appears in 1/4 pages (< 3 pages) -> should NOT be removed
    assert "Chinh sach VSmartPay" not in cleaned[0]
    assert "Footer VSmartPay 2026" not in cleaned[0]
    assert "Footer khac" in cleaned[3]


def test_pdf_scan_detection_fails_helper():
    from app.modules.documents.service import DocumentService
    from unittest.mock import patch, MagicMock
    
    service = DocumentService()
    
    # Mock PyMuPDF fitz.open to return pages where > 50% are scanned (fewer than 100 characters)
    mock_doc = MagicMock()
    mock_page1 = MagicMock()
    mock_page1.get_text.return_value = [(0, 0, 100, 100, "It text", 0, 0)] # < 100 characters
    mock_page2 = MagicMock()
    mock_page2.get_text.return_value = [(0, 0, 100, 100, "Cung rat it text", 0, 0)] # < 100 characters
    mock_page3 = MagicMock()
    mock_page3.get_text.return_value = [(0, 0, 100, 100, "A" * 150, 0, 0)] # > 100 characters
    
    mock_doc.__len__.return_value = 3
    mock_doc.load_page.side_effect = [mock_page1, mock_page2, mock_page3]
    
    with patch("fitz.open", return_value=mock_doc):
        with pytest.raises(ValueError, match="file scan ch\u01b0a \u0111\u01b0\u1ee3c h\u1ed7 tr\u1ee3"):
            service.parser.extract_text("scanned.pdf", b"%PDF-1.4\nscanned")


def test_smart_chunking_with_markdown():
    from app.modules.documents.service import DocumentService
    
    service = DocumentService()
    
    markdown_text = (
        "# Huong dan dang ky\n"
        "Buoc 1: Mo ung dung VSmartPay tren dien thoai di dong cua ban.\n"
        "## Yeu cau dang ky\n"
        "Ban can phai co so dien thoai hop le va can cuoc cong dan con han su dung.\n"
    )
    
    extracted_pages = [
        {"text": markdown_text, "page": 1, "heading": None}
    ]
    
    chunks = service.chunker.chunk_document(extracted_pages, chunk_size=100, chunk_overlap=10)
    assert len(chunks) > 0
    
    # Heading should be extracted from markdown header splitter metadata
    assert chunks[0]["heading"] == "Huong dan dang ky"
    # The sub-chunk should inherit the heading Yeu cau dang ky
    sub_chunk_headings = [c["heading"] for c in chunks if "Yeu cau dang ky" in c["content"] or (c["heading"] and "Yeu cau dang ky" in c["heading"])]
    assert len(sub_chunk_headings) > 0

