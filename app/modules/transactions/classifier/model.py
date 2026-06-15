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

def classify_transaction(description: str) -> dict:
    text_clean = clean_text(description)
    
    # Rule engine trước
    rule_result = rule_classify(text_clean)
    if rule_result:
        return {"label": rule_result, "source": "rule", "confidence": 1.0}
    
    # Model nếu không match rule
    classifier = get_classifier()
    result = classifier(text_clean)[0]
    
    if result["score"] < THRESHOLD:
        return {"label": "Khác", "source": "model", "confidence": result["score"]}
    
    return {
        "label": result["label"],
        "source": "model", 
        "confidence": round(result["score"], 3)
    }