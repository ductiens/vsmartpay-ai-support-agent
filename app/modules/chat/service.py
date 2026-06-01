import os
import re
import json
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
        Runs through LangGraph multi-agent orchestration when settings.USE_LANGGRAPH=True.
        Falls back to the legacy ChatService pipeline when settings.USE_LANGGRAPH=False.
        """
        if settings.USE_LANGGRAPH:
            from app.core.graph import execute_graph
            return await execute_graph(request)

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

        # Check if RAG context is insufficient
        context_insufficient = len(context_parts) == 0

        # Step 4: Execute mock wallet tools based on intent
        tool_calls = []
        transaction_status = None
        transaction_id = None
        transaction_type = None
        amount = None
        balance_data = None
        txn_data = None
        fee_data = None
        
        # BALANCE_INQUIRY → call check_balance
        if intent_info.intent == "BALANCE_INQUIRY":
            from app.modules.tools.mock_wallet import check_balance
            balance_data = check_balance(request.user_id)
            tool_calls.append({
                "tool_name": "check_balance",
                "arguments": {"user_id": request.user_id},
                "result": balance_data
            })
            
        # TRANSACTION_STATUS → extract transaction_id, call get_transaction_status
        elif intent_info.intent == "TRANSACTION_STATUS":
            # Extract transaction ID (e.g. txn_001, tx_001) using regex
            match = re.search(r"\b(txn_\d+|tx_\d+)\b", request.message, re.IGNORECASE)
            transaction_id = match.group(1) if match else None
            
            from app.modules.tools.mock_wallet import get_transaction_status
            if transaction_id:
                txn_data = get_transaction_status(transaction_id)
                if txn_data:
                    transaction_status = txn_data.get("status")
                tool_calls.append({
                    "tool_name": "get_transaction_status",
                    "arguments": {"transaction_id": transaction_id},
                    "result": txn_data or {"error": f"Giao dịch {transaction_id} không tồn tại."}
                })
            else:
                # No transaction ID in user message
                tool_calls.append({
                    "tool_name": "get_transaction_status",
                    "arguments": {"transaction_id": None},
                    "result": {"error": "Không tìm thấy mã giao dịch trong tin nhắn."}
                })
                
        # FEE_INQUIRY → extract transaction_type & amount, call get_fee
        elif intent_info.intent == "FEE_INQUIRY":
            msg_lower = request.message.lower()
            transaction_type = "TRANSFER"
            if "rút" in msg_lower or "withdraw" in msg_lower:
                transaction_type = "WITHDRAWAL"
            elif "nạp" in msg_lower or "deposit" in msg_lower:
                transaction_type = "DEPOSIT"
                
            # Default amount is 500,000 VND, else parse from message
            amount = 500000
            k_match = re.search(r"(\d+(?:\.\d+)?)\s*k\b", msg_lower)
            if k_match:
                amount = int(float(k_match.group(1)) * 100) if '.' in k_match.group(1) else int(k_match.group(1)) * 1000
            else:
                m_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:tr triệu|triệu|tr)\b", msg_lower)
                if m_match:
                    amount = int(float(m_match.group(1)) * 1000000)
                else:
                    nums = re.findall(r"\b\d+(?:[\.,]\d+)*\b", request.message)
                    for num in nums:
                        cleaned = num.replace(".", "").replace(",", "")
                        val = int(cleaned)
                        if val > 1000:
                            amount = val
                            break
                            
            from app.modules.tools.mock_wallet import get_fee
            fee_data = get_fee(transaction_type, amount)
            tool_calls.append({
                "tool_name": "get_fee",
                "arguments": {"transaction_type": transaction_type, "amount": amount},
                "result": fee_data
            })

        # Step 5: Evaluate escalation policies
        esc_info = await self.escalation_service.evaluate_escalation(
            user_id=request.user_id,
            last_message=request.message,
            intent=intent_info.intent,
            confidence=intent_info.confidence,
            context_insufficient=context_insufficient,
            transaction_status=transaction_status
        )
        
        required = esc_info.required
        reason = esc_info.reason
        priority = esc_info.priority
        
        # If escalation is required, call create_support_ticket and save ticket to MongoDB
        if required:
            # Map intent to support issue type
            issue_type = "GENERAL_SUPPORT"
            if intent_info.intent == "FRAUD_OR_SCAM_REPORT" or "lừa đảo" in request.message.lower() or "mất tiền" in request.message.lower():
                issue_type = "FRAUD"
            elif intent_info.intent == "ACCOUNT_SECURITY" or "bị hack" in request.message.lower() or "otp" in request.message.lower():
                issue_type = "SECURITY"
            elif transaction_status is not None:
                issue_type = "TRANSACTION"
            elif intent_info.intent == "REFUND_OR_DISPUTE":
                issue_type = "REFUND"
                
            from app.modules.tools.mock_wallet import create_support_ticket
            ticket_data = await create_support_ticket(
                user_id=request.user_id,
                issue_type=issue_type,
                message=request.message
            )
            
            tool_calls.append({
                "tool_name": "create_support_ticket",
                "arguments": {
                    "user_id": request.user_id,
                    "issue_type": issue_type,
                    "message": request.message
                },
                "result": ticket_data
            })

        # Step 6: Build grounded prompt
        context_str = "\n\n".join(context_parts) if context_parts else "Không tìm thấy thông tin phù hợp trong tài liệu hướng dẫn."
        
        tool_context = ""
        if tool_calls:
            tool_context = "\n--- Kết quả từ Hệ thống Ví giả lập ---\n"
            for tc in tool_calls:
                tool_context += f"Công cụ được gọi: {tc['tool_name']}\nTham số: {json.dumps(tc['arguments'], ensure_ascii=False)}\nKết quả trả về: {json.dumps(tc['result'], ensure_ascii=False)}\n\n"
            tool_context += "---------------------------------------\n\n"

        system_instruction = (
            "Bạn là nhân viên tư vấn ảo hỗ trợ khách hàng xuất sắc của ví điện tử VSmartPay.\n"
            "Hãy trả lời câu hỏi của khách hàng bằng tiếng Việt lịch sự, thân thiện và tuân thủ các quy tắc nghiêm ngặt sau:\n"
            "1. CHỈ TRẢ LỜI dựa trên các thông tin được cung cấp trong phần 'Ngữ cảnh tài liệu' và 'Kết quả từ Hệ thống Ví giả lập' dưới đây. Tuyệt đối không tự suy diễn hoặc bịa đặt các thông số hạn mức, phần trăm hay biểu phí nếu tài liệu không đề cập.\n"
            "2. TUYỆT ĐỐI KHÔNG YÊU CẦU khách hàng cung cấp các thông tin nhạy cảm bảo mật như mã OTP, mật khẩu tài khoản đăng nhập hay số thẻ ngân hàng đầy đủ.\n"
            "3. Nếu thông tin trong tài liệu và hệ thống ví giả lập không đủ để trả lời câu hỏi, hoặc cần chuyển giao cho bộ phận CSKH, hãy thông báo rõ ràng rằng yêu cầu đã được ghi nhận hỗ trợ trực tiếp.\n"
        )
        
        user_prompt = (
            f"--- Ngữ cảnh tài liệu ---\n"
            f"{context_str}\n"
            f"---------------------------\n\n"
            f"{tool_context}"
            f"Câu hỏi của khách hàng: {request.message}\n"
            f"Phản hồi của bạn:"
        )

        answer = ""
        # Call OpenAI Chat API if key is present
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            # Primary robust local fallback answers based on tool results and escalation
            if intent_info.intent == "BALANCE_INQUIRY" and balance_data:
                answer = f"Chào bạn, số dư khả dụng hiện tại trong tài khoản ví VSmartPay của bạn là {balance_data.get('balance', 0):,} {balance_data.get('currency', 'VND')}."
            elif intent_info.intent == "TRANSACTION_STATUS":
                if txn_data and "error" not in txn_data:
                    status_vi = {
                        "SUCCESS": "Thành công",
                        "PENDING": "Đang chờ xử lý",
                        "FAILED": "Thất bại",
                        "REFUNDED": "Đã hoàn tiền"
                    }.get(txn_data["status"], txn_data["status"])
                    
                    answer = f"Chào bạn, mã giao dịch {transaction_id} của bạn có trạng thái là: **{status_vi}**. Số tiền giao dịch: {txn_data.get('amount', 0):,} {txn_data.get('currency', 'VND')}."
                    if txn_data["status"] in ["FAILED", "PENDING"]:
                        answer += f" Vì giao dịch đang có trạng thái {status_vi}, hệ thống đã tự động tạo yêu cầu chuyển giao cho bộ phận CSKH để hỗ trợ bạn ngay lập tức."
                else:
                    answer = f"Chào bạn, hệ thống ví không tìm thấy thông tin cho mã giao dịch {transaction_id or 'đã nhập'}. Bạn vui lòng kiểm tra chính xác mã giao dịch."
            elif intent_info.intent == "FEE_INQUIRY" and fee_data:
                tx_type_str = transaction_type or "TRANSFER"
                type_vi = {
                    "TRANSFER": "Chuyển tiền",
                    "WITHDRAWAL": "Rút tiền",
                    "DEPOSIT": "Nạp tiền"
                }.get(tx_type_str.upper(), tx_type_str)
                answer = f"Chào bạn, phí áp dụng cho giao dịch {type_vi} với số tiền {amount or 0:,} VND là **{fee_data.get('fee', 0):,} VND**."
            elif required:
                answer = f"Chào bạn, yêu cầu của bạn đã được ghi nhận hỗ trợ trực tiếp từ con người. Hệ thống đã tự động tạo một ticket hỗ trợ (mức độ ưu tiên: {priority}) gửi đến bộ phận CSKH với lý do: {reason}. Nhân viên hỗ trợ sẽ liên hệ với bạn trong thời gian sớm nhất."
            elif len(context_parts) > 0 and "không tìm thấy" not in context_str.lower():
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
                if retrieved_chunks:
                    answer = f"Đã xảy ra sự cố kỹ thuật khi kết nối dịch vụ LLM. Dựa trên tài liệu tra cứu: {retrieved_chunks[0].text[:250]}..."
                else:
                    answer = "Đã xảy ra sự cố kỹ thuật khi kết nối dịch vụ LLM. Hiện tại tôi chưa tìm thấy tài liệu tra cứu tương ứng."

        # Step 7: Log assistant message in MongoDB
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
            tool_calls=tool_calls,
            escalation=EscalationDetail(
                required=required,
                reason=reason,
                priority=priority
            )
        )
