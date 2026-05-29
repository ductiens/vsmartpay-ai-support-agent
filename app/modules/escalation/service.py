from typing import Optional
from app.modules.escalation.policy import EscalationPolicy
from app.modules.escalation.schema import EscalationResponse

class EscalationService:
    def __init__(self):
        self.policy = EscalationPolicy()

    async def evaluate_escalation(
        self,
        user_id: str,
        last_message: str,
        intent: str = "FAQ_GENERAL",
        confidence: float = 1.0,
        context_insufficient: bool = False,
        transaction_status: Optional[str] = None
    ) -> EscalationResponse:
        """
        Check if the last user message should be escalated to human agents based on 6 criteria.
        """
        required, reason, priority = self.policy.check_escalation(
            message=last_message,
            intent=intent,
            confidence=confidence,
            context_insufficient=context_insufficient,
            transaction_status=transaction_status
        )
        
        return EscalationResponse(
            required=required,
            reason=reason,
            priority=priority
        )
