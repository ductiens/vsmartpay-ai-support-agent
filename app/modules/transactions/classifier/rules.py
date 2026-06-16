RULES = {
    "Ăn uống": ["cf ", "cafe", "coffee", "highlands", "baemin", 
                "shopeefood", "grabfood", "an sang", "an trua", 
                "an toi", "com ", "bun ", "pho ", "tra sua"],
    "Di chuyển": ["grab ", "gojek", "be ", "xang ", "do xang", 
                  "ve xe", "taxi", "gui xe", "thue xe", "cao toc"],
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

def remove_accents(input_str: str) -> str:
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])

def rule_classify(text: str) -> str | None:
    text_unaccented = remove_accents(text).lower()
    for label, keywords in RULES.items():
        if any(kw in text_unaccented for kw in keywords):
            return label
    return None