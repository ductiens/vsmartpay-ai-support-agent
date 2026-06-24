import json
import re
from typing import List, Dict, Any
from app.config import settings
from app.modules.rag.retriever import RAGRetriever

async def run_rag_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    RAG Agent: Lấy context từ Retrieval, gọi LLM để sinh draft_answer.
    Nếu có streaming_queue trong state, sẽ đẩy từng chữ vào queue.
    """
    streamed_to_queue = False
    
    user_message = state.get("user_message", "") or ""
    intent = state.get("intent", "FAQ_GENERAL")
    kb_type = state.get("kb_type")
    agent_scope = state.get("agent_scope")
    user_id = state.get("user_id", "")
    
    # Cập nhật: Lấy danh sách sub_queries từ state. Tương thích ngược: nếu rỗng, dùng user_message.
    sub_queries = state.get("sub_queries")
    if not sub_queries:
        sub_queries = [user_message]
    
    # 1. Retrieve relevant chunks using RAGRetriever with scoping filters
    tool_only_intents = ["BALANCE_INQUIRY", "TRANSACTION_HISTORY", "TRANSACTION_STATUS"]
    if intent in tool_only_intents or intent == "BOT_IDENTITY":
        retrieved_chunks = []
    else:
        retriever = RAGRetriever()
        
        import asyncio
        async def fetch_for_query(q):
            return await retriever.retrieve(
                query=q,
                top_k=settings.TOP_K,
                agent_scope=agent_scope,
                kb_type=kb_type
            )
                
        # Thực thi tìm kiếm RAG song song
        results_nested = await asyncio.gather(*[fetch_for_query(q) for q in sub_queries])
        
        # Gom kết quả, deduplicate theo chunk_id (chỉ giữ chunk điểm cao nhất)
        chunk_map = {}
        for res_list in results_nested:
            for c in res_list:
                c_id = getattr(c, "id", None) if hasattr(c, "id") else (c.get("id") if isinstance(c, dict) else id(c))
                score = getattr(c, "score", 0.0) if hasattr(c, "score") else (c.get("score", 0.0) if isinstance(c, dict) else 0.0)
                
                if c_id not in chunk_map:
                    chunk_map[c_id] = c
                else:
                    existing = chunk_map[c_id]
                    existing_score = getattr(existing, "score", 0.0) if hasattr(existing, "score") else (existing.get("score", 0.0) if isinstance(existing, dict) else 0.0)
                    if score > existing_score:
                        chunk_map[c_id] = c
                        
        # Sắp xếp theo score giảm dần và lấy Top-K chunk tốt nhất
        retrieved_chunks_all = list(chunk_map.values())
        retrieved_chunks_all.sort(key=lambda x: getattr(x, "score", 0.0) if hasattr(x, "score") else (x.get("score", 0.0) if isinstance(x, dict) else 0.0), reverse=True)
        retrieved_chunks = retrieved_chunks_all[:settings.TOP_K]
    
    # Calculate retrieval score, doc_ids, sources
    retrieval_score = 0.0
    doc_ids = []
    sources = []
    context_parts = []
    
    for c in retrieved_chunks:
        score = float(c.score)
        if score > retrieval_score:
            retrieval_score = score
            
        source_file = c.metadata.get("source", "unknown")
        doc_ids.append(source_file)
        
        sources.append({
            "doc_id": source_file,
            "chunk_id": c.id,
            "title": c.metadata.get("category", "Tài liệu VSmartPay") + f" - {source_file}",
            "score": score
        })
        
        # Keep chunks with similarity >= 0.35 for the prompt context
        if score >= 0.35:
            context_parts.append(f"### [Nguồn: {source_file} - ID: {c.id}]:\n{c.text}")
            
    # Set full metadata filter object for transparency
    retrieval_filter = {}
    if agent_scope:
        retrieval_filter["agent_scope"] = agent_scope
    if kb_type:
        retrieval_filter["kb_type"] = kb_type
 
    # 2. Build draft answer using OpenAI or local fallback
    tool_calls = state.get("tool_calls", [])
    
    # Format tool context
    tool_context = ""
    balance_data = None
    txn_data = None
    fee_data = None
    transaction_id = None
    transaction_type = None
    amount = None
    
    if tool_calls:
        tool_context = "\n--- Kết quả từ Hệ thống Ví giả lập ---\n"
        for tc in tool_calls:
            tool_name = tc.get("tool_name")
            arguments = tc.get("arguments", {})
            result = tc.get("result")
            
            tool_context += f"Công cụ được gọi: {tool_name}\nTham số: {json.dumps(arguments, ensure_ascii=False)}\nKết quả trả về: {json.dumps(result, ensure_ascii=False)}\n\n"
            
            if tool_name == "check_balance":
                balance_data = result
            elif tool_name == "get_transaction_status":
                txn_data = result
                transaction_id = arguments.get("transaction_id")
            elif tool_name == "get_fee":
                fee_data = result
                transaction_type = arguments.get("transaction_type")
                amount = arguments.get("amount")
        tool_context += "---------------------------------------\n\n"
 
    if intent in tool_only_intents or intent == "BOT_IDENTITY":
        context_str = ""
    else:
        context_str = "\n\n".join(context_parts) if context_parts else "Không tìm thấy thông tin phù hợp trong tài liệu hướng dẫn."
    
    api_key = settings.OPENAI_API_KEY
    model = settings.OPENAI_MODEL
    draft_answer = ""
    
    if intent == "BOT_IDENTITY":
        draft_answer = (
            "Chào bạn, tôi là trợ lý ảo hỗ trợ khách hàng của ví điện tử VSmartPay. "
            "Tôi có thể hỗ trợ bạn các vấn đề liên quan đến ví như kiểm tra số dư, tra cứu lịch sử giao dịch, "
            "giải đáp thắc mắc về biểu phí, hạn mức giao dịch, hoặc hướng dẫn liên kết thẻ ngân hàng."
        )
    elif not api_key or api_key == "your_openai_api_key_here":
        # Fallback answers based on tool results or retrieved chunks
        if intent == "BALANCE_INQUIRY" and balance_data:
            draft_answer = f"Chào bạn, số dư khả dụng hiện tại trong tài khoản ví VSmartPay của bạn là {balance_data.get('balance', 0):,} {balance_data.get('currency', 'VND')}."
        elif intent == "TRANSACTION_STATUS":
            if txn_data and "error" not in txn_data:
                status_vi = {
                    "SUCCESS": "Thành công",
                    "PENDING": "Đang chờ xử lý",
                    "FAILED": "Thất bại",
                    "REFUNDED": "Đã hoàn tiền"
                }.get(txn_data["status"], txn_data["status"])
                draft_answer = f"Chào bạn, mã giao dịch {transaction_id} của bạn có trạng thái là: **{status_vi}**. Số tiền giao dịch: {txn_data.get('amount', 0):,} {txn_data.get('currency', 'VND')}."
                if txn_data["status"] in ["FAILED", "PENDING"]:
                    draft_answer += f" Vì giao dịch đang có trạng thái {status_vi}, hệ thống đã tự động tạo yêu cầu chuyển giao cho bộ phận CSKH để hỗ trợ bạn ngay lập tức."
            elif txn_data and "error" in txn_data:
                draft_answer = txn_data["error"]
            else:
                draft_answer = f"Chào bạn, hệ thống ví không tìm thấy thông tin cho mã giao dịch {transaction_id or 'đã nhập'}. Bạn vui lòng kiểm tra chính xác mã giao dịch."
        elif intent == "FEE_INQUIRY" and fee_data:
            tx_type_str = transaction_type or "TRANSFER"
            type_vi = {
                "TRANSFER": "Chuyển tiền",
                "WITHDRAWAL": "Rút tiền",
                "DEPOSIT": "Nạp tiền"
            }.get(tx_type_str.upper(), tx_type_str)
            draft_answer = f"Chào bạn, phí áp dụng cho giao dịch {type_vi} với số tiền {amount or 0:,} VND là **{fee_data.get('fee', 0):,} VND**."
        elif len(context_parts) > 0:
            draft_answer = f"Dựa trên tài liệu VSmartPay về {retrieved_chunks[0].metadata.get('category', 'tài liệu')}: {retrieved_chunks[0].text[:300]}..."
        else:
            draft_answer = "Xin lỗi, hiện tại tôi chưa tìm thấy thông tin tương ứng trong tài liệu hỗ trợ. Tôi có thể đề xuất kết nối bạn đến nhân viên hỗ trợ trực tiếp (CSKH) để xử lý tình huống này."
    else:
        try:
            from langchain_openai import ChatOpenAI
            from langchain_core.messages import SystemMessage, HumanMessage
            client = ChatOpenAI(model=model, api_key=api_key, temperature=0.2)
            
            system_instruction = (
                "Bạn là nhân viên tư vấn ảo hỗ trợ khách hàng xuất sắc của ví điện tử VSmartPay.\n"
                "Hãy trả lời câu hỏi của khách hàng bằng tiếng Việt lịch sự, thân thiện và tuân thủ các quy tắc nghiêm ngặt sau:\n"
                "1. CHỈ TRẢ LỜI dựa trên các thông tin được cung cấp trong phần 'Ngữ cảnh tài liệu' và 'Kết quả từ Hệ thống Ví giả lập' dưới đây. Tuyệt đối không tự suy diễn hoặc bịa đặt các thông số hạn mức, phần trăm hay biểu phí nếu tài liệu không đề cập.\n"
                "2. TUYỆT ĐỐI KHÔNG YÊU CẦU khách hàng cung cấp các thông tin nhạy cảm bảo mật như mã OTP, mật khẩu tài khoản đăng nhập hay số thẻ ngân hàng đầy đủ.\n"
                "3. Nếu thông tin trong tài liệu và hệ thống ví giả lập không đủ để trả lời câu hỏi, hoặc cần chuyển giao cho bộ phận CSKH, hãy thông báo rõ ràng rằng yêu cầu đã được ghi nhận hỗ trợ trực tiếp.\n"
            )
            
            doc_context_section = ""
            if context_str:
                doc_context_section = (
                    f"--- Ngữ cảnh tài liệu ---\n"
                    f"{context_str}\n"
                    f"---------------------------\n\n"
                )
                
            user_prompt = (
                f"{doc_context_section}"
                f"{tool_context}"
                f"Câu hỏi của khách hàng: {user_message}\n"
                f"Phản hồi của bạn:"
            )
            
            queue = state.get("streaming_queue")
            draft_answer = ""
            messages = [
                SystemMessage(content=system_instruction),
                HumanMessage(content=user_prompt)
            ]
            
            if queue:
                # Still support the legacy queue if needed
                async for chunk in client.astream(messages):
                    token = chunk.content
                    if isinstance(token, str) and token:
                        draft_answer += token
                        await queue.put({"type": "token", "content": token})
                    elif isinstance(token, list):
                        for item in token:
                            if isinstance(item, str):
                                draft_answer += item
                                await queue.put({"type": "token", "content": item})
                            elif isinstance(item, dict) and "text" in item:
                                text_item = item["text"]
                                if isinstance(text_item, str):
                                    draft_answer += text_item
                                    await queue.put({"type": "token", "content": text_item})
                streamed_to_queue = True
            else:
                response = await client.ainvoke(messages)
                content = response.content
                if isinstance(content, str):
                    draft_answer = content
                elif isinstance(content, list):
                    draft_answer = "".join(
                        str(item) if isinstance(item, str) 
                        else str(item.get("text", "")) if isinstance(item, dict) 
                        else "" for item in content
                    )
                else:
                    draft_answer = str(content) if content else ""
        except Exception as e:
            print(f"DEBUG LLM ERROR: {type(e).__name__} - {str(e)}")
            if intent == "BALANCE_INQUIRY" and balance_data:
                draft_answer = f"Đã xảy ra sự cố kỹ thuật khi kết nối dịch vụ LLM. Tuy nhiên, số dư khả dụng hiện tại trong tài khoản ví VSmartPay của bạn là {balance_data.get('balance', 0):,} {balance_data.get('currency', 'VND')}."
            elif intent == "TRANSACTION_STATUS" and txn_data:
                status_vi = {
                    "SUCCESS": "Thành công",
                    "PENDING": "Đang chờ xử lý",
                    "FAILED": "Thất bại",
                    "REFUNDED": "Đã hoàn tiền"
                }.get(txn_data.get("status", ""), txn_data.get("status", ""))
                draft_answer = f"Đã xảy ra sự cố kỹ thuật khi kết nối dịch vụ LLM. Tuy nhiên, mã giao dịch {transaction_id} của bạn có trạng thái là: **{status_vi}**. Số tiền giao dịch: {txn_data.get('amount', 0):,} {txn_data.get('currency', 'VND')}."
            elif intent == "FEE_INQUIRY" and fee_data:
                tx_type_str = transaction_type or "TRANSFER"
                type_vi = {
                    "TRANSFER": "Chuyển tiền",
                    "WITHDRAWAL": "Rút tiền",
                    "DEPOSIT": "Nạp tiền"
                }.get(tx_type_str.upper(), tx_type_str)
                draft_answer = f"Đã xảy ra sự cố kỹ thuật khi kết nối dịch vụ LLM. Tuy nhiên, phí áp dụng cho giao dịch {type_vi} với số tiền {amount or 0:,} VND là **{fee_data.get('fee', 0):,} VND**."
            elif retrieved_chunks:
                draft_answer = f"Đã xảy ra sự cố kỹ thuật khi kết nối dịch vụ LLM. Dựa trên tài liệu tra cứu: {retrieved_chunks[0].text[:250]}..."
            else:
                draft_answer = "Đã xảy ra sự cố kỹ thuật khi kết nối dịch vụ LLM và không có tài liệu cục bộ khả dụng."
                
    queue = state.get("streaming_queue")
    if queue and not streamed_to_queue and draft_answer:
        await queue.put({"type": "token", "content": draft_answer})

    return {
        "retrieved_chunks": retrieved_chunks,
        "retrieval_score": retrieval_score,
        "doc_ids": doc_ids,
        "sources": sources,
        "retrieval_filter": retrieval_filter,
        "draft_answer": draft_answer
    }
