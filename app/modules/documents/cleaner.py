import re
import unicodedata
from collections import Counter
from typing import List


def clean_text(text: str) -> str:
    """
    Làm sạch văn bản theo các bước:
    - Chuẩn hóa Unicode tiếng Việt về NFC.
    - Xóa số trang.
    - Xóa dòng trống thừa (giữ tối đa 1 dòng trống liên tiếp).
    """
    if not text:
        return ""
        
    # 1. Chuẩn hóa NFC
    text = unicodedata.normalize('NFC', text)
    
    # 2. Xóa số trang (ví dụ: "Trang 1", "Page 1 of 5", "Trang 1 / 10", v.v.)
    text = re.sub(r'(?i)\b(trang|page)\s*\d+(\s*of\s*\d+|\s*/\s*\d+)?\b', '', text)
    
    # Xóa các dòng chỉ chứa chữ số đơn lẻ (ví dụ số trang đứng độc lập ở đầu/cuối trang)
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        if re.match(r'^\s*\d+\s*$', line):
            continue
        cleaned_lines.append(line)
    text = "\n".join(cleaned_lines)
    
    # Nối các từ bị gãy dòng bằng dấu gạch ngang
    text = text.replace('-\n', '')
    
    # Sửa lỗi gãy dòng (ngắt giữa chừng / chữ dính nhau) trong PDF
    # Thay thế \n đơn lẻ thành khoảng trắng, ngoại trừ khi dòng tiếp theo là list (-, *, 1.) hoặc table (|)
    text = re.sub(r'(?<!\n)\n(?!\n)(?![\-\*\|]|\d+\.)', ' ', text)
    
    # 3. Xóa dòng trống thừa (giữ tối đa 1 dòng trống liên tiếp)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()


def remove_repeated_headers_footers(pages_text: List[str]) -> List[str]:
    """
    Tự động phát hiện và loại bỏ các header/footer lặp lại trên nhiều trang.
    Dòng được coi là header/footer lặp lại nếu xuất hiện ở đầu/cuối trang
    trong ít nhất 3 trang và chiếm >= 30% tổng số trang.
    """
    n_pages = len(pages_text)
    if n_pages < 3:
        return pages_text
        
    first_lines = []
    last_lines = []
    
    for page in pages_text:
        lines = [line.strip() for line in page.split("\n") if line.strip()]
        if lines:
            first_lines.append(lines[0])
            if len(lines) > 1:
                last_lines.append(lines[-1])
                
    threshold = max(3, int(n_pages * 0.3))
    
    first_counts = Counter(first_lines)
    last_counts = Counter(last_lines)
    
    headers_to_remove = {line for line, count in first_counts.items() if count >= threshold}
    footers_to_remove = {line for line, count in last_counts.items() if count >= threshold}
    
    cleaned_pages = []
    for page in pages_text:
        lines = page.split("\n")
        new_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped in headers_to_remove or stripped in footers_to_remove:
                continue
            new_lines.append(line)
        cleaned_pages.append("\n".join(new_lines))
        
    return cleaned_pages
