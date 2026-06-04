import re
from typing import Optional, Tuple

class EscalationPolicy:
    def __init__(self):
        # A list of keywords or phrases that trigger immediate human escalation
        self.trigger_keywords = [
            "lừa đảo", "bị mất tiền", "hack", "khóa tài khoản",
            "cảnh sát", "pháp luật", "kiện", "nhân viên hỗ trợ"
        ]
        
        # Detailed security terms for specific high-risk category detection
        self.security_keywords = [
            "mất tiền", "thất thoát", "bị trừ tiền", "không thấy tiền", "trừ tiền",
            "bị hack", "hacker", "hack", "bị xâm nhập", "bị đăng nhập lạ",
            "lộ otp", "mất otp", "chia sẻ otp", "gửi otp", "lộ mã otp"
        ]
        
        # Human support request terms
        self.human_keywords = [
            "gặp nhân viên", "cskh", "tư vấn viên", "gặp tư vấn", "gặp hỗ trợ"
        ]

    def should_escalate(self, message: str) -> bool:
        """Backward compatible check for basic keyword matching."""
        message_lower = message.lower()
        for kw in self.trigger_keywords:
            if kw in message_lower:
                return True
        return False

    def check_escalation(
        self,
        message: str,
        intent: str,
        confidence: float,
        context_insufficient: bool,
        transaction_status: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Evaluate all 6 escalation policy criteria.
        Returns a tuple: (required: bool, reason: Optional[str], priority: Optional[str])
        """
        msg_lower = message.lower()
        
        # 1. Intent is HUMAN_SUPPORT_REQUEST, FRAUD_OR_SCAM_REPORT, or REFUND_OR_DISPUTE
        # 2. User reports lost money, being hacked, or OTP leakage (via keywords)
        
        # Check security-related keywords first (Lost money, hacked, OTP leak) -> HIGH Priority
        for kw in self.security_keywords:
            if kw in msg_lower:
                return True, f"Báo cáo sự cố bảo mật hoặc nghi ngờ bị lừa đảo lạm dụng tài chính: phát hiện từ khóa '{kw}'", "HIGH"
        
        # Check explicit security intent taxonomy -> HIGH Priority
        if intent in ["FRAUD_OR_SCAM_REPORT", "ACCOUNT_SECURITY"]:
            return True, "Báo cáo sự cố bảo mật hoặc nghi ngờ bị lừa đảo lạm dụng tài chính.", "HIGH"
            
        # Check human agent or refund dispute intent -> MEDIUM Priority
        if intent in ["HUMAN_SUPPORT_REQUEST", "REFUND_OR_DISPUTE"]:
            return True, "Khách hàng yêu cầu hỗ trợ trực tiếp từ con người hoặc tranh chấp hoàn tiền.", "MEDIUM"
            
        # Check explicit human support keywords -> MEDIUM Priority
        for kw in self.human_keywords:
            if kw in msg_lower:
                return True, "Khách hàng yêu cầu hỗ trợ trực tiếp từ con người.", "MEDIUM"

        # 3. Transaction status is FAILED or PENDING beyond normal threshold
        if transaction_status is not None:
            tx_status_upper = transaction_status.upper()
            if tx_status_upper == "FAILED":
                return True, "Giao dịch có trạng thái Thất bại (FAILED).", "HIGH"
            elif tx_status_upper == "PENDING":
                return True, "Giao dịch có trạng thái Chờ xử lý (PENDING) ngoài ngưỡng thông thường.", "MEDIUM"

        # 4. Confidence score is below threshold (< 0.6)
        if confidence < 0.6:
            return True, f"Độ tin cậy phân loại ý định thấp ({confidence} < 0.6).", "LOW"

        # 5. Retrieved context is insufficient
        sensitive_intents = {
            "TRANSFER_GUIDE",
            "FEE_INQUIRY",
            "LIMIT_INQUIRY",
            "ACCOUNT_SECURITY",
            "FAILED_TRANSACTION",
            "REFUND_OR_DISPUTE",
            "FRAUD_OR_SCAM_REPORT",
            "HUMAN_SUPPORT_REQUEST"
        }
        if context_insufficient and intent in sensitive_intents:
            return True, "Tài liệu hướng dẫn hiện tại không đủ thông tin để trả lời câu hỏi nhạy cảm.", "LOW"

        # 6. Question is OUT_OF_SCOPE
        if intent == "OUT_OF_SCOPE":
            return True, "Yêu cầu nằm ngoài phạm vi hỗ trợ của ví.", "LOW"

        # Basic legacy keywords matching as a fallback
        if self.should_escalate(message):
            return True, "Chuyển giao do phát hiện từ khóa rủi ro/yêu cầu nhân viên.", "MEDIUM"

        return False, None, None
