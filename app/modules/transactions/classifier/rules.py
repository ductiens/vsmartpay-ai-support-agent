RULES = {
    "Ăn uống": ["cf ", "cafe", "coffee", "highlands", "baemin", 
                "shopeefood", "grabfood", "an sang", "an trua", 
                "an toi", "com ", "bun ", "pho ", "tra sua"],
    "Di chuyển": ["grab ", "gojek", "be ", "xang ", "do xang", 
                  "ve xe", "taxi", "gui xe", "thue xe", "cao toc", "xanh sm"],
    "Hóa đơn & Tiện ích": ["tien dien", "tien nuoc", "cuoc ", "fpt", 
                            "viettel", "vnpt", "mobifone", "phi quan ly", 
                            "tra gop", "bao hiem", "phi chung cu"],
    "Mua sắm": ["shopee", "tiki", "lazada", "di cho", "sieu thi",
                "vinmart", "coopmart"],
    "Giải trí": ["netflix", "spotify", "cgv", "karaoke", "kara ",
                 "bowling", "pubg", "game "],
    "Sức khỏe": ["kham benh", "benh vien", "vinmec", "thuoc ", 
                 "nha khoa", "gym ", "yoga", "cat toc", "massage"],
    "Giáo dục": ["hoc phi", "khoa hoc", "udemy", "coursera", 
                 "hoc tieng", "hoc lai xe"],
    "Chuyển tiền cá nhân": ["gui me", "gui ba", "tra no", 
                             "mung sinh nhat", "chia tien"],
}

import unicodedata

# --- LLM Integration cho Rules (Commented out for ML demo) ---
# from openai import OpenAI
# import os
#
# def expand_rules_with_llm(existing_rules: dict) -> dict:
#     """
#     Dùng LLM để tự động phân tích các giao dịch chưa nhận diện được
#     và tự động sinh thêm các từ khóa mới vào RULES.
#     (Đã comment lại để demo Rule cứng và ML)
#     """
#     # client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
#     # prompt = f"Dựa vào tập luật hiện tại: {existing_rules}, hãy đề xuất thêm 5 từ khóa phổ biến mới cho mỗi danh mục."
#     # ... (Gọi API và cập nhật từ điển RULES) ...
#     # return updated_rules
# -------------------------------------------------------------

def remove_accents(input_str: str) -> str:
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])

def rule_classify(text: str) -> str | None:
    text_unaccented = remove_accents(text).lower()
    for label, keywords in RULES.items():
        if any(kw in text_unaccented for kw in keywords):
            return label
            
    # --- LLM Zero-shot classification ngay trong Rule Engine (Đã comment) ---
    # llm_label = llm_zero_shot_classify(text)
    # if llm_label in RULES.keys():
    #     return llm_label
    # ------------------------------------------------------------------------
    
    return None