from app.modules.chat.schema import ChatRequest, ChatResponse, EscalationDetail
from app.modules.chat.repository import ChatRepository
from app.modules.intents.classifier import IntentClassifier
from app.modules.escalation.service import EscalationService
from app.modules.rag.service import RAGService

class ChatService:
    def __init__(self):
        self.repository = ChatRepository()
        self.intent_classifier = IntentClassifier()
        self.escalation_service = EscalationService()
        self.rag_service = RAGService()

    async def process_message(self, request: ChatRequest) -> ChatResponse:
        """
        Coordinate intent classification, RAG retrieval, escalation check, 
        and wallet tool integration to formulate a response.
        (Phase 1: Return the temporary response required by the user)
        """
        # Save user message to database history asynchronously
        await self.repository.save_message(request.session_id, "user", request.message)
        
        # Call placeholder services to simulate the flow
        intent_info = await self.intent_classifier.classify_intent(request.message)
        esc_info = await self.escalation_service.evaluate_escalation(request.user_id, request.message)
        
        # Save assistant message to history
        assistant_answer = "VSmartPay AI Support Agent is not fully configured yet."
        await self.repository.save_message(request.session_id, "assistant", assistant_answer)
        
        return ChatResponse(
            answer=assistant_answer,
            intent=intent_info.intent,
            sources=[],
            tool_calls=[],
            escalation=EscalationDetail(
                required=esc_info.required,
                reason=esc_info.reason
            )
        )
