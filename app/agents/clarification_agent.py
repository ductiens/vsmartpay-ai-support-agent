from typing import Dict, Any
from app.config import settings

async def run_clarification_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Formulate a polite response asking the customer to clarify their inquiry
    because the retrieval was ungrounded or the confidence score was low.
    """
    user_message = state.get("user_message", "")
    intent = state.get("intent", "FAQ_GENERAL")
    
    api_key = settings.OPENAI_API_KEY
    model = settings.OPENAI_MODEL
    final_answer = ""
    
    if not api_key or api_key == "your_openai_api_key_here":
        final_answer = (
            "Chào bạn, hiện tại tôi chưa tìm thấy thông tin tương ứng trong tài liệu hỗ trợ. "
            "Bạn vui lòng cung cấp thêm thông tin chi tiết hoặc làm rõ câu hỏi để tôi có thể tra cứu "
            "và hỗ trợ bạn tốt nhất nhé!"
        )
    else:
        try:
            from openai import AsyncOpenAI
            from langsmith.wrappers import wrap_openai
            client = wrap_openai(AsyncOpenAI(api_key=api_key))
            
            system_instruction = (
                "Bạn là nhân viên tư vấn khách hàng ảo của ví điện tử VSmartPay.\n"
                "Hiện tại, câu trả lời tự động có độ tin cậy thấp hoặc không tìm thấy đủ nguồn tài liệu chính thống.\n"
                "Nhiệm vụ của bạn là viết một phản hồi tiếng Việt cực kỳ lịch sự, thân thiện và tự nhiên, "
                "yêu cầu khách hàng giải thích/cung cấp thêm chi tiết hoặc viết rõ ràng hơn câu hỏi của họ.\n"
                "Tránh nói quá máy móc, hãy giữ sự chân thành và sẵn sàng phục vụ."
            )
            
            user_prompt = (
                f"Câu hỏi gốc của khách hàng: {user_message}\n"
                f"Ý định phân loại được: {intent}\n"
                f"Hãy phản hồi lịch sự yêu cầu làm rõ:"
            )
            
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.5
            )
            final_answer = response.choices[0].message.content or ""
        except Exception:
            final_answer = (
                "Chào bạn, hiện tại tôi chưa tìm thấy thông tin tương ứng trong tài liệu hỗ trợ. "
                "Bạn vui lòng cung cấp thêm thông tin chi tiết hoặc làm rõ câu hỏi để tôi có thể tra cứu "
                "và hỗ trợ bạn tốt nhất nhé!"
            )
            
    return {
        "final_answer": final_answer
    }
