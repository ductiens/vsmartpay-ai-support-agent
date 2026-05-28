from app.modules.escalation.policy import EscalationPolicy
from app.modules.escalation.schema import EscalationResponse

class EscalationService:
    def __init__(self):
        self.policy = EscalationPolicy()

    async def evaluate_escalation(self, user_id: str, last_message: str) -> EscalationResponse:
        """
        Check if the last user message should be escalated to human agents based on policy.
        """
        if self.policy.should_escalate(last_message):
            return EscalationResponse(
                required=True,
                reason="Triggered by high-risk keywords or user request for agent."
            )
        return EscalationResponse(required=False, reason=None)
