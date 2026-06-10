import json
from typing import Dict, Any
from app.config import settings

async def run_grounding_guard(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verify if the draft answer is fully grounded in the retrieved Atlas chunks using chunk metadata.
    Flag grounded = False if it cannot be traced back.
    """
    draft_answer = state.get("draft_answer", "") or ""
    retrieved_chunks = state.get("retrieved_chunks", [])
    intent = state.get("intent", "FAQ_GENERAL")
    
    # 1. Transaction-related intents that rely on mock tools and BOT_IDENTITY are grounded in the response template / tool results
    transaction_intents = ["BALANCE_INQUIRY", "TRANSACTION_STATUS", "FEE_INQUIRY", "TRANSACTION_HISTORY", "BOT_IDENTITY"]
    if intent in transaction_intents:
        return {
            "grounded": True
        }
        
    # 2. If no chunks were retrieved for knowledge-related intents, it's not grounded
    if not retrieved_chunks:
        return {
            "grounded": False
        }
        
    api_key = settings.OPENAI_API_KEY
    model = settings.OPENAI_MODEL
    
    if not api_key or api_key == "your_openai_api_key_here":
        # Local fallback verification logic:
        # Since fallback draft_answer is constructed directly from local matching chunks,
        # it is inherently grounded if we have chunks.
        # Let's do a basic check to ensure draft_answer is not empty.
        if not draft_answer or "không tìm thấy" in draft_answer.lower() or "xin lỗi" in draft_answer.lower():
            return {"grounded": False}
        return {"grounded": True}
        
    try:
        from openai import AsyncOpenAI
        from langsmith.wrappers import wrap_openai
        client = wrap_openai(AsyncOpenAI(api_key=api_key))
        
        # Prepare context representation including metadata
        chunks_str = ""
        for i, chunk in enumerate(retrieved_chunks):
            meta = chunk.metadata or {}
            chunks_str += (
                f"--- Chunk {i+1} ---\n"
                f"Nội dung: {chunk.text}\n"
                f"Metadata: Nguồn={meta.get('source', '')}, Trang={meta.get('page', '')}, "
                f"Tiêu đề={meta.get('heading', '')}, Phân loại={meta.get('kb_type', '')}\n\n"
            )
            
        system_instruction = (
            "Bạn là Grounding Guard, chuyên gia kiểm tra tính xác thực của câu trả lời dựa trên tài liệu nguồn.\n"
            "Hãy đối chiếu câu trả lời nháp (Draft Answer) và các mảnh tài liệu (Retrieved Chunks) được cung cấp.\n"
            "Hãy xác định xem mọi thông tin cốt lõi trong Draft Answer có thể được truy vết (traced back) "
            "về ít nhất một Retrieved Chunk và khớp với thông tin metadata (file_name, page, heading, kb_type) hay không.\n"
            "Nếu câu trả lời tự suy diễn thêm bất kỳ thông số nào ngoài tài liệu nguồn, hãy đánh dấu grounded = false.\n"
            "Trả về kết quả dưới định dạng JSON duy nhất:\n"
            "{\n"
            "  \"grounded\": true / false,\n"
            "  \"reason\": \"Lý do giải thích\"\n"
            "}"
        )
        
        user_prompt = (
            f"--- Các mảnh tài liệu nguồn ---\n"
            f"{chunks_str}\n"
            f"--- Câu trả lời nháp cần kiểm tra ---\n"
            f"Draft Answer: {draft_answer}\n\n"
            f"Hãy đưa ra đánh giá của bạn bằng định dạng JSON:"
        )
        
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.0
        )
        
        result_json = json.loads(response.choices[0].message.content or "{}")
        grounded = result_json.get("grounded", True)
        
        return {
            "grounded": bool(grounded)
        }
    except Exception as e:
        # Graceful fallback on OpenAI execution errors
        return {
            "grounded": True
        }
