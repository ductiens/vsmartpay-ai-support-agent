from app.modules.intents.schema import IntentClassification
from app.modules.intents.taxonomy import IntentTaxonomy

class IntentClassifier:
    async def classify_intent(self, message: str) -> IntentClassification:
        """
        Classify user query into an intent. 
        (Phase 1: Basic keyword-based fallback logic)
        """
        msg_lower = message.lower()
        
        if any(w in msg_lower for w in ["số dư", "tiền còn lại", "tài khoản", "balance"]):
            return IntentClassification(intent=IntentTaxonomy.WALLET_BALANCE.value, confidence=0.9)
        
        if any(w in msg_lower for w in ["giao dịch", "lịch sử", "chuyển tiền", "nhận tiền", "transaction"]):
            return IntentClassification(intent=IntentTaxonomy.TRANSACTION_HISTORY.value, confidence=0.9)
            
        if any(w in msg_lower for w in ["phí", "biểu phí", "fee", "cost"]):
            return IntentClassification(intent=IntentTaxonomy.SYSTEM_FEES.value, confidence=0.9)
            
        if any(w in msg_lower for w in ["hạn mức", "limit"]):
            return IntentClassification(intent=IntentTaxonomy.FAQ_LIMITS.value, confidence=0.8)
            
        if any(w in msg_lower for w in ["điều khoản", "quy định", "terms"]):
            return IntentClassification(intent=IntentTaxonomy.FAQ_TERMS.value, confidence=0.8)
            
        if any(w in msg_lower for w in ["lỗi", "không được", "thất bại", "hỏng", "trouble"]):
            return IntentClassification(intent=IntentTaxonomy.FAQ_TROUBLESHOOTING.value, confidence=0.8)

        if any(w in msg_lower for w in ["nhân viên", "người thật", "chuyển tiếp", "human", "agent"]):
            return IntentClassification(intent=IntentTaxonomy.ESC_HUMAN.value, confidence=0.95)
            
        return IntentClassification(intent=IntentTaxonomy.FAQ_GENERAL.value, confidence=0.5)
