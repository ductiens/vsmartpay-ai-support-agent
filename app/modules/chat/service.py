import os
from typing import List, Dict, Any, Optional
from app.config import settings
from app.modules.chat.schema import ChatRequest, ChatResponse, ChatSource, EscalationDetail
from app.modules.chat.repository import ChatRepository
from app.modules.intents.classifier import IntentClassifier
from app.modules.escalation.service import EscalationService
from app.modules.rag.retriever import RAGRetriever

class ChatService:
    def __init__(self):
        self.repository = ChatRepository()
        self.intent_classifier = IntentClassifier()
        self.escalation_service = EscalationService()
        self.retriever = RAGRetriever()
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.OPENAI_MODEL

    async def process_message(self, request: ChatRequest) -> ChatResponse:
        """
        Main chat flow:
        1. Log user message & session in MongoDB Atlas.
        2. Classify intent (rule-based).
        3. Retrieve relevant chunks (FAISS RAG).
        4. Check escalation policies.
        5. Build grounded prompt and call OpenAI.
        6. Log assistant answer and return response.
        """
        # Step 1: Log session and user message in MongoDB
        await self.repository.log_session(request.session_id, request.user_id)
        await self.repository.log_message(
            session_id=request.session_id,
            role="user",
            content=request.message
        )

        # Step 2: Classify intent
        intent_info = await self.intent_classifier.classify_intent(request.message)
        
        # Step 3: Retrieve top-k documents (FAISS)
        retrieved_chunks = await self.retriever.retrieve(request.message, top_k=settings.TOP_K)
        
        # Filter sources with positive score to show in response
        sources = []
        context_parts = []
        
        for c in retrieved_chunks:
            # FlatIP of normalized vectors returns Cosine similarity score
            score = float(c.score)
            
            # Map chunk metadata
            source_file = c.metadata.get("source", "unknown")
            sources.append(ChatSource(
                doc_id=source_file,
                chunk_id=c.id,
                title=c.metadata.get("category", "Tài liệu VSmartPay") + f" - {source_file}",
                score=score
            ))
            
            # Use chunks with reasonable score for grounding prompt
            if score >= 0.35:
                context_parts.append(f"### [Nguồn: {source_file} - ID: {c.id}]:\n{c.text}")

        # Step 4: Evaluate escalation
        esc_info = await self.escalation_service.evaluate_escalation(request.user_id, request.message)
        
        # Check specific escalation rules
        priority = None
        required = esc_info.required
        reason = esc_info.reason
        
        # Immediate High priority rules
        if intent_info.intent in ["FRAUD_OR_SCAM_REPORT", "ACCOUNT_SECURITY"] or "lừa đảo" in request.message.lower() or "bị hack" in request.message.lower():
            required = True
            reason = "Báo cáo sự cố bảo mật hoặc nghi ngờ bị lừa đảo lạm dụng tài chính."
            priority = "HIGH"
        # Medium priority human support requests
        elif intent_info.intent == "HUMAN_SUPPORT_REQUEST" or "gặp nhân viên" in request.message.lower() or "cskh" in request.message.lower():
            required = True
            reason = "Khách hàng yêu cầu hỗ trợ trực tiếp từ con người."
            priority = "MEDIUM"

        # Step 5: Build grounded prompt
        context_str = "\n\n".join(context_parts) if context_parts else "Không tìm thấy thông tin phù hợp trong tài liệu."
        
        system_instruction = (
            "Bạn là nhân viên tư vấn ảo hỗ trợ khách hàng xuất sắc của ví điện tử VSmartPay.\n"
            "Hãy trả lời câu hỏi của khách hàng bằng tiếng Việt lịch sự, thân thiện và tuân thủ các quy tắc nghiêm ngặt sau:\n"
            "1. CHỈ TRẢ LỜI dựa trên các thông tin được cung cấp trong phần 'Ngữ cảnh tài liệu' dưới đây. Tuyệt đối không tự suy diễn hoặc bịa đặt các thông số hạn mức, phần trăm hay biểu phí nếu tài liệu không đề cập.\n"
            "2. TUYỆT ĐỐI KHÔNG YÊU CẦU khách hàng cung cấp các thông tin nhạy cảm bảo mật như mã OTP, mật khẩu tài khoản đăng nhập hay số thẻ ngân hàng đầy đủ.\n"
            "3. Nếu thông tin trong tài liệu không đủ để trả lời câu hỏi, bạn phải ghi nhận rõ ràng là 'Không đủ thông tin' và đề xuất khách hàng kết nối gặp nhân viên hỗ trợ trực tiếp.\n"
        )
        
        user_prompt = (
            f"--- Ngữ cảnh tài liệu ---\n"
            f"{context_str}\n"
            f"---------------------------\n\n"
            f"Câu hỏi của khách hàng: {request.message}\n"
            f"Phản hồi của bạn:"
        )

        answer = ""
        # Call OpenAI Chat API if key is present
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            # Mock fallback answer matching RAG chunks
            if len(context_parts) > 0 and "không tìm thấy" not in context_str.lower():
                answer = f"Dựa trên tài liệu VSmartPay về {retrieved_chunks[0].metadata.get('category', 'tài liệu')}: {retrieved_chunks[0].text[:300]}..."
            else:
                answer = "Xin lỗi, hiện tại tôi chưa tìm thấy thông tin tương ứng trong tài liệu hỗ trợ. Tôi có thể đề xuất kết nối bạn đến nhân viên hỗ trợ trực tiếp (CSKH) để xử lý tình huống này."
        else:
            try:
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=self.api_key)
                response = await client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.2
                )
                answer = response.choices[0].message.content or ""
            except Exception as e:
                # Safe fallback
                answer = f"Đã xảy ra sự cố kỹ thuật khi kết nối dịch vụ LLM. Dựa trên tài liệu tra cứu: {retrieved_chunks[0].text[:250]}..."

        # Step 6: Log assistant message in MongoDB
        # Convert ChatSource list to dictionaries for saving
        logged_sources = [{"doc_id": s.doc_id, "chunk_id": s.chunk_id, "title": s.title, "score": s.score} for s in sources]
        await self.repository.log_message(
            session_id=request.session_id,
            role="assistant",
            content=answer,
            intent=intent_info.intent,
            sources=logged_sources
        )

        return ChatResponse(
            answer=answer,
            intent=intent_info.intent,
            confidence=intent_info.confidence,
            sources=sources,
            tool_calls=[],
            escalation=EscalationDetail(
                required=required,
                reason=reason,
                priority=priority
            )
        )
