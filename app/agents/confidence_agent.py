from typing import Dict, Any
from app.modules.escalation.service import EscalationService

async def run_confidence_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate response confidence and run the Escalation Service policy criteria 
    to decide if human handoff (escalation) is required.
    """
    user_id = state.get("user_id", "")
    user_message = state.get("user_message", "")
    intent = state.get("intent", "FAQ_GENERAL")
    intent_confidence = state.get("confidence", 0.5)
    retrieved_chunks = state.get("retrieved_chunks", [])
    tool_calls = state.get("tool_calls", [])
    grounded = state.get("grounded", True)
    
    # 1. Determine if context is insufficient (no chunks with similarity >= 0.35)
    context_parts_count = sum(1 for c in retrieved_chunks if float(c.score) >= 0.35)
    context_insufficient = context_parts_count == 0
    
    # 2. Extract transaction_status if get_transaction_status tool was run
    transaction_status = None
    for tc in tool_calls:
        if tc.get("tool_name") == "get_transaction_status":
            res = tc.get("result")
            if res and isinstance(res, dict):
                transaction_status = res.get("status")
                
    # 3. Call EscalationService
    escalation_service = EscalationService()
    esc_info = await escalation_service.evaluate_escalation(
        user_id=user_id,
        last_message=user_message,
        intent=intent,
        confidence=intent_confidence,
        context_insufficient=context_insufficient,
        transaction_status=transaction_status
    )
    
    # 4. Determine overall confidence score
    # Default to intent_confidence
    overall_confidence = intent_confidence
    
    if intent in ["BALANCE_INQUIRY", "TRANSACTION_STATUS", "FEE_INQUIRY"]:
        # High confidence since it is sourced directly from mock systems
        overall_confidence = 0.95
    elif not grounded:
        overall_confidence = 0.4
    elif not context_insufficient:
        overall_confidence = 0.9
    else:
        overall_confidence = 0.5
        
    return {
        "confidence": overall_confidence,
        "escalation_required": esc_info.required,
        "escalation_reason": esc_info.reason or ""
    }
