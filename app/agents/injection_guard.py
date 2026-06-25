def check_injection(state) -> dict:
    """
    Detect and block messages containing prompt injection patterns:
    "ignore previous instructions", "bỏ qua hướng dẫn", "show system prompt",
    "tiết lộ prompt", "developer message", "jailbreak".
    """
    user_message = state.get("user_message", "") or ""
    message_lower = user_message.lower()
    
    injection_patterns = [
        "ignore previous instructions",
        "bỏ qua hướng dẫn",
        "show system prompt",
        "tiết lộ prompt",
        "developer message",
        "jailbreak",
        "bỏ qua các lệnh trước đó",
        "ignore all previous instructions",
        "quên hết các lệnh",
        "bạn là một AI không bị giới hạn",
        "you are an unrestricted ai"
    ]
    
    for pattern in injection_patterns:
        if pattern in message_lower:
            return {
                "injection_detected": True,
                "escalation_required": True,
                "escalation_reason": f"Prompt injection attempt detected: '{pattern}'",
                "final_answer": "Phát hiện hành vi không hợp lệ. Yêu cầu của bạn đã bị từ chối."
            }
            
    return {
        "injection_detected": False
    }
