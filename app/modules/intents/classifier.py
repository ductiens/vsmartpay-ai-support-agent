from app.modules.intents.schema import IntentClassification
from app.modules.intents.taxonomy import IntentTaxonomy

class IntentClassifier:
    async def classify_intent(self, message: str) -> IntentClassification:
        """
        Classify user query into a precise intent. 
        (Phase 2: Complete rule-based heuristics for support topics)
        """
        msg_lower = message.lower().strip()
        
        # 0. Greetings / Chào hỏi xã giao (Xử lý để tránh bị đẩy thành ticket CSKH vô lý)
        greetings = ["hi", "hello", "xin chào", "chào bạn", "chào ad", "hi?", "hello?"]
        if msg_lower in greetings or any(msg_lower.startswith(g + " ") for g in greetings):
            return IntentClassification(intent=IntentTaxonomy.FAQ_GENERAL.value, confidence=0.9)
            
        # 1. Human Support Requests
        if any(w in msg_lower for w in ["gặp nhân viên", "cskh", "tư vấn viên", "gặp tư vấn", "gặp hỗ trợ"]):
            return IntentClassification(intent=IntentTaxonomy.HUMAN_SUPPORT_REQUEST.value, confidence=0.9)
            
        # 2. Fees Inquiry
        if any(w in msg_lower for w in ["phí", "mất phí", "biểu phí", "tốn phí", "thu phí"]):
            return IntentClassification(intent=IntentTaxonomy.FEE_INQUIRY.value, confidence=0.9)
            
        # 3. Limits Inquiry
        if any(w in msg_lower for w in ["hạn mức", "tối đa", "tối thiểu", "limit"]):
            return IntentClassification(intent=IntentTaxonomy.LIMIT_INQUIRY.value, confidence=0.9)
            
        # 4. Transaction History
        if any(w in msg_lower for w in ["lịch sử", "gần đây", "history"]):
            return IntentClassification(intent=IntentTaxonomy.TRANSACTION_HISTORY.value, confidence=0.95)
            
        # 4b. Transaction Status
        if any(w in msg_lower for w in ["giao dịch", "mã giao dịch", "trạng thái"]):
            return IntentClassification(intent=IntentTaxonomy.TRANSACTION_STATUS.value, confidence=0.95)
            
        # 5. Balance Inquiry
        if any(w in msg_lower for w in ["số dư", "balance", "tài khoản còn bao nhiêu"]):
            return IntentClassification(intent=IntentTaxonomy.BALANCE_INQUIRY.value, confidence=0.9)

        # 6. Fraud or Scam Report
        if any(w in msg_lower for w in ["lừa đảo", "mất tiền", "scam", "bị gạt"]):
            return IntentClassification(intent=IntentTaxonomy.FRAUD_OR_SCAM_REPORT.value, confidence=0.95)

        # 7. Account Security
        if any(w in msg_lower for w in ["bị hack", "otp", "mật khẩu", "đổi mật khẩu", "pin", "khóa tài khoản"]):
            return IntentClassification(intent=IntentTaxonomy.ACCOUNT_SECURITY.value, confidence=0.9)

        # 8. KYC Support
        if any(w in msg_lower for w in ["kyc", "xác thực danh tính", "xác minh"]):
            return IntentClassification(intent=IntentTaxonomy.KYC_SUPPORT.value, confidence=0.9)

        # 9. Bank Linking
        if any(w in msg_lower for w in ["liên kết ngân hàng", "liên kết thẻ", "hủy liên kết"]):
            return IntentClassification(intent=IntentTaxonomy.BANK_LINKING.value, confidence=0.9)

        # 10. Failed Transaction
        if any(w in msg_lower for w in ["lỗi giao dịch", "thất bại", "không chuyển được", "bị treo"]):
            return IntentClassification(intent=IntentTaxonomy.FAILED_TRANSACTION.value, confidence=0.85)

        # 11. Promotions
        if any(w in msg_lower for w in ["khuyến mãi", "ưu đãi", "quà", "gift"]):
            return IntentClassification(intent=IntentTaxonomy.PROMOTION_INQUIRY.value, confidence=0.9)
            
        # Fallback default
        return IntentClassification(intent=IntentTaxonomy.FAQ_GENERAL.value, confidence=0.5)
