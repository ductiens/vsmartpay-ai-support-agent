import re
from typing import List, Dict, Any, Optional
import tiktoken

from app.config import settings


class DocumentChunker:
    def __init__(self):
        self._tokenizer = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        return len(self._tokenizer.encode(text))

    def chunk_document(
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
            length_function=self.count_tokens,
            separators=["\n\n", ". ", "\n", " ", ""]
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
                    breadcrumbs = []
                    if heading:
                        breadcrumbs.append(heading)
                    for h_level in ["Header 1", "Header 2", "Header 3", "Header 4"]:
                        if h_level in hc.metadata:
                            breadcrumbs.append(hc.metadata[h_level])
                            
                    if breadcrumbs:
                        active_heading = " > ".join(breadcrumbs)
                    else:
                        active_heading = heading
                            
                    # Nếu chunk sau khi tách vẫn quá lớn, tiếp tục dùng Recursive
                    if self.count_tokens(hc.page_content) > chunk_size:
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
