from typing import Dict, Any
from app.modules.tools.mock_wallet import create_support_ticket
from app.modules.escalation.service import EscalationService

async def run_escalation_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle the escalation process: determine ticket priority, create support ticket in MongoDB,
    and format the final escalation response for the user.
    """
    user_id = state.get("user_id", "")
    user_message = state.get("user_message", "")
    intent = state.get("intent", "FAQ_GENERAL")
    escalation_reason = state.get("escalation_reason", "Yêu cầu chuyển giao hỗ trợ trực tiếp.")
    tool_calls = list(state.get("tool_calls", []))
    
    # 0. If prompt injection was detected, bypass everything and return the warning answer directly
    if state.get("injection_detected"):
        return {
            "final_answer": "Phát hiện hành vi không hợp lệ. Yêu cầu của bạn đã bị từ chối.",
            "escalation_required": True,
            "escalation_reason": escalation_reason,
            "tool_calls": tool_calls
        }
        
    # 1. Determine issue type based on intent and user message
    issue_type = "GENERAL_SUPPORT"
    message_lower = user_message.lower()
    
    # Get transaction status if any
    transaction_status = None
    for tc in tool_calls:
        if tc.get("tool_name") == "get_transaction_status":
            res = tc.get("result")
            if res and isinstance(res, dict):
                transaction_status = res.get("status")
                
    if intent == "FRAUD_OR_SCAM_REPORT" or "lừa đảo" in message_lower or "mất tiền" in message_lower:
        issue_type = "FRAUD"
    elif intent == "ACCOUNT_SECURITY" or "bị hack" in message_lower or "otp" in message_lower:
        issue_type = "SECURITY"
    elif transaction_status is not None:
        issue_type = "TRANSACTION"
    elif intent == "REFUND_OR_DISPUTE":
        issue_type = "REFUND"
        
    # 2. Call EscalationService to get priority
    escalation_service = EscalationService()
    esc_info = await escalation_service.evaluate_escalation(
        user_id=user_id,
        last_message=user_message,
        intent=intent,
        context_insufficient=True,  # Force/simulate for getting priority
        transaction_status=transaction_status
    )
    priority = esc_info.priority or "MEDIUM"
    
    # 3. Call tool to create support ticket in MongoDB
    ticket_data = await create_support_ticket(
        user_id=user_id,
        issue_type=issue_type,
        message=user_message
    )
    
    # Save the tool call in tool_calls list
    tool_calls.append({
        "tool_name": "create_support_ticket",
        "arguments": {
            "user_id": user_id,
            "issue_type": issue_type,
            "message": user_message
        },
        "result": ticket_data
    })
    
    # 4. Formulate the final escalation answer
    final_answer = (
        f"Chào bạn, yêu cầu của bạn đã được ghi nhận hỗ trợ trực tiếp từ con người. "
        f"Hệ thống đã tự động tạo một ticket hỗ trợ (mức độ ưu tiên: {priority}) gửi đến bộ phận CSKH "
        f"với lý do: {escalation_reason or 'Khách hàng yêu cầu hỗ trợ trực tiếp.'}. "
        f"Nhân viên hỗ trợ sẽ liên hệ với bạn trong thời gian sớm nhất."
    )
    
    # Let's also store the escalation details in metadata
    metadata = dict(state.get("metadata", {}))
    metadata["escalation"] = {
        "required": True,
        "reason": escalation_reason,
        "priority": priority,
        "ticket_id": ticket_data.get("ticket_id")
    }
    
    return {
        "final_answer": final_answer,
        "tool_calls": tool_calls,
        "metadata": metadata,
        "escalation_required": True,
        "escalation_reason": escalation_reason
    }
