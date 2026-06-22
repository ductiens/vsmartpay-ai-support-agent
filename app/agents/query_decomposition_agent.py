import json
import re
from typing import Dict, Any, List
from app.config import settings

def _is_simple_query(message: str) -> bool:
    """
    Heuristic để kiểm tra xem câu hỏi có đơn giản hay không.
    Trả về True nếu câu hỏi đơn giản (không cần phân rã).
    """
    msg = message.lower().strip()
    
    # Kiểm tra độ dài: nếu quá ngắn (dưới 20 ký tự), thường là đơn giản
    if len(msg) < 20:
        return True
        
    # Kiểm tra các từ nối ám chỉ nhiều ý
    complex_conjunctions = [" và ", " nhưng ", " đồng thời ", "?", " ngoài ra ", " mặt khác "]
    
    # Nếu câu hỏi chứa từ nối hoặc nhiều dấu chấm hỏi, có thể phức tạp
    has_complex_conjunction = any(conj in msg for conj in complex_conjunctions)
    question_marks = msg.count("?")
    
    if has_complex_conjunction or question_marks > 1:
        return False
        
    return True

async def run_query_decomposition_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Phân rã câu hỏi phức tạp của user thành nhiều sub-queries.
    """
    user_message = state.get("user_message", "") or ""
    
    # 1. Tối ưu Chi phí & Latency (Heuristic)
    if _is_simple_query(user_message):
        return {"sub_queries": [user_message]}
        
    # 2. Sử dụng LLM để phân rã nếu câu hỏi phức tạp
    api_key = settings.OPENAI_API_KEY
    model = settings.OPENAI_MODEL
    
    # Fallback nếu không có API key
    if not api_key or api_key == "your_openai_api_key_here":
        return {"sub_queries": [user_message]}
        
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage, HumanMessage
        
        client = ChatOpenAI(model=model, api_key=api_key, temperature=0.1)
        
        system_instruction = (
            "Bạn là một chuyên gia phân tích ngữ nghĩa. Nhiệm vụ của bạn là phân rã một câu hỏi phức tạp "
            "từ người dùng thành các câu hỏi đơn giản, độc lập để hệ thống dễ dàng tìm kiếm thông tin.\n"
            "Chỉ trả về danh sách dưới dạng JSON array of strings. Tuyệt đối KHÔNG trả về bất kỳ văn bản nào khác ngoài JSON.\n"
            "Ví dụ:\n"
            "Người dùng: 'Làm sao để nạp tiền vào ví và phí rút tiền hiện tại là bao nhiêu?'\n"
            'Output: ["Làm sao để nạp tiền vào ví VSmartPay?", "Phí rút tiền ví VSmartPay hiện tại là bao nhiêu?"]'
        )
        
        messages = [
            SystemMessage(content=system_instruction),
            HumanMessage(content=user_message)
        ]
        
        response = await client.ainvoke(messages)
        content = str(response.content).strip()
        
        # Clean up in case LLM added markdown formatting like ```json ... ```
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
        
        parsed_list = json.loads(content)
        
        if isinstance(parsed_list, list) and len(parsed_list) > 0:
            # 3. Giới hạn số lượng (Max limit): Tối đa 3 sub-queries
            MAX_SUB_QUERIES = 3
            sub_queries = parsed_list[:MAX_SUB_QUERIES]
            # Ensure all items are strings
            sub_queries = [str(q) for q in sub_queries]
            return {"sub_queries": sub_queries}
        else:
            # Result is not a valid list or is empty
            return {"sub_queries": [user_message]}
            
    except Exception as e:
        print(f"DEBUG DECOMPOSITION LLM ERROR: {type(e).__name__} - {str(e)}")
        # 4. Fallback (Lỗi parse LLM)
        return {"sub_queries": [user_message]}
