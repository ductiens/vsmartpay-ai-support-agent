class EscalationPolicy:
    def __init__(self):
        # A list of keywords or phrases that trigger immediate human escalation
        self.trigger_keywords = [
            "lừa đảo", "bị mất tiền", "hack", "khóa tài khoản",
            "cảnh sát", "pháp luật", "kiện", "nhân viên hỗ trợ"
        ]

    def should_escalate(self, message: str) -> bool:
        message_lower = message.lower()
        for kw in self.trigger_keywords:
            if kw in message_lower:
                return True
        return False
