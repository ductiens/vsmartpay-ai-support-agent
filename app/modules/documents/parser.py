import io
import os
import zipfile
from typing import List, Dict, Any, Optional
import docx

from app.modules.documents.cleaner import clean_text, remove_repeated_headers_footers


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


class DocumentParser:
    def extract_text(self, file_name: str, file_bytes: bytes) -> List[Dict[str, Any]]:
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
                
                # 1. Trích xuất Tables
                tables_md = []
                if hasattr(page, "find_tables"):
                    tabs = page.find_tables()  # type: ignore
                    for tab in tabs:
                        rows = tab.extract()
                        if not rows:
                            continue
                        
                        header = [str(c).strip().replace("\n", " ") if c is not None else "" for c in rows[0]]
                        markdown_lines = []
                        markdown_lines.append("| " + " | ".join(header) + " |")
                        markdown_lines.append("| " + " | ".join(["---"] * len(header)) + " |")
                        for row in rows[1:]:
                            row_clean = [str(c).strip().replace("\n", " ") if c is not None else "" for c in row]
                            if len(row_clean) < len(header):
                                row_clean.extend([""] * (len(header) - len(row_clean)))
                            elif len(row_clean) > len(header):
                                row_clean = row_clean[:len(header)]
                            markdown_lines.append("| " + " | ".join(row_clean) + " |")
                        tables_md.append("\n".join(markdown_lines))
                
                # 2. Trích xuất Text blocks (loại bỏ header/footer sát lề)
                blocks = page.get_text("blocks")  # type: ignore[attr-defined]
                text_blocks = []
                page_rect = page.rect
                
                for b in blocks:
                    if b[6] == 0:  # block type 0 is text
                        x0, y0, x1, y1, text_content, block_no, block_type = b
                        # Bỏ qua text quá sát mép trên hoặc mép dưới (ví dụ margin 50 pixel)
                        if y0 < 50 or y1 > page_rect.height - 50:
                            continue
                        text_blocks.append(text_content)
                
                # Gộp blocks và tables
                page_text = "\n\n".join(text_blocks + tables_md)
                
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
            for item in iter_block_items(doc):
                if isinstance(item, docx.text.paragraph.Paragraph):
                    style_name = item.style.name.lower() if (item.style and item.style.name) else ""
                    text = item.text.strip()
                    if not text:
                        continue
                        
                    if style_name and "heading 1" in style_name:
                        text_lines.append(f"# {text}")
                    elif "heading 2" in style_name:
                        text_lines.append(f"## {text}")
                    elif "heading 3" in style_name:
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
                "heading": None
            })
            
        else:
            raise ValueError("Unsupported file type")

        return extracted_pages
