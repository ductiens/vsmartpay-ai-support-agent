import re
from transformers import pipeline
from functools import lru_cache
from .rules import rule_classify

HF_MODEL_ID = "ductiens/transaction-classifier"
THRESHOLD = 0.5

def clean_text(text: str) -> str:
    text = str(text).lower().strip()
    text = re.sub(r"[^\w\s\u00C0-\u024F\u1E00-\u1EFF]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

@lru_cache(maxsize=1)
def get_classifier():
    """Load model 1 lần duy nhất, cache lại dùng mãi."""
    return pipeline(
        "text-classification",
        model=HF_MODEL_ID,
        device=-1  # CPU, đổi thành 0 nếu có GPU
    )

import logging

logger = logging.getLogger(__name__)

# --- LLM Integration (Commented out for ML demo) ---
# from openai import OpenAI
# import os
#
# def llm_classify(description: str) -> dict:
#     """
#     Dùng LLM (OpenAI) để phân loại các giao dịch mà Rule và ML Model đều không tự tin.
#     (Đã comment lại vì hiện tại chỉ muốn demo ML/Rules)
#     """
#     # client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
#     # prompt = f"Phân loại giao dịch sau vào 1 trong các danh mục: Ăn uống, Di chuyển, Hóa đơn & Tiện ích, Mua sắm, Giải trí, Sức khỏe, Giáo dục, Chuyển tiền cá nhân, Khác.\n\nGiao dịch: '{description}'\n\nChỉ trả về tên danh mục."
#     # response = client.chat.completions.create(
#     #     model="gpt-4o-mini",
#     #     messages=[{"role": "user", "content": prompt}]
#     # )
#     # label = response.choices[0].message.content.strip()
#     # return {"label": label, "source": "llm", "confidence": 0.9}
# ---------------------------------------------------

def classify_transaction(description: str) -> dict:
    text_clean = clean_text(description)
    
    # Rule engine trước
    rule_result = rule_classify(text_clean)
    if rule_result:
        return {"label": rule_result, "source": "rule", "confidence": 1.0}
    
    # Model nếu không match rule
    try:
        classifier = get_classifier()
        result = classifier(text_clean)[0]
        
        if result["score"] >= THRESHOLD:
            return {
                "label": result["label"],
                "source": "model", 
                "confidence": round(result["score"], 3)
            }
            
        # --- Gọi LLM Fallback nếu ML Model có độ tin cậy thấp (Dưới THRESHOLD) ---
        # llm_result = llm_classify(description)
        # if llm_result:
        #     return llm_result
        # -------------------------------------------------------------------------
        
        return {"label": "Khác", "source": "model", "confidence": result["score"]}
        
    except Exception as e:
        logger.warning(f"Classification model error or offline: {e}. Fallback to rule engine only.")
        
        # --- Gọi LLM Fallback nếu ML Model bị lỗi ---
        # try:
        #     return llm_classify(description)
        # except Exception as llm_e:
        #     logger.warning(f"LLM fallback error: {llm_e}")
        # --------------------------------------------
        
        return {"label": "Khác", "source": "fallback_error", "confidence": 0.0}