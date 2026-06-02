from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from app.config import settings

class ChatAnswerChain:
    def __init__(self):
        # 1. System Prompt matching the exact business requirements
        self.system_prompt = (
            "Bạn là nhân viên tư vấn ảo hỗ trợ khách hàng xuất sắc của ví điện tử VSmartPay.\n"
            "Hãy trả lời câu hỏi của khách hàng bằng tiếng Việt lịch sự, thân thiện và tuân thủ các quy tắc nghiêm ngặt sau:\n"
            "1. CHỈ TRẢ LỜI dựa trên các thông tin được cung cấp trong phần 'Ngữ cảnh tài liệu' và 'Kết quả từ Hệ thống Ví giả lập' dưới đây. Tuyệt đối không tự suy diễn hoặc bịa đặt các thông số hạn mức, phần trăm hay biểu phí nếu tài liệu không đề cập.\n"
            "2. TUYỆT ĐỐI KHÔNG YÊU CẦU khách hàng cung cấp các thông tin nhạy cảm bảo mật như mã OTP, mật khẩu tài khoản đăng nhập hay số thẻ ngân hàng đầy đủ.\n"
            "3. Nếu thông tin trong tài liệu và hệ thống ví giải lập không đủ để trả lời câu hỏi, hoặc cần chuyển giao cho bộ phận CSKH, hãy thông báo rõ ràng rằng yêu cầu đã được ghi nhận hỗ trợ trực tiếp.\n"
        )
        
        # 2. User Prompt matching the legacy formatting
        self.user_prompt_template = (
            "--- Ngữ cảnh tài liệu ---\n"
            "{context}\n"
            "---------------------------\n\n"
            "{tool_context}"
            "Câu hỏi của khách hàng: {message}\n"
            "Phản hồi của bạn:"
        )

        # 3. Create the LangChain ChatPromptTemplate
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("user", self.user_prompt_template)
        ])

    async def generate_answer(self, message: str, context: str, tool_context: str) -> str:
        """
        Generate grounded answer using LangChain Expression Language (LCEL).
        """
        # Lazy model initialization to prevent constructor crashes in local tests/eval environments
        llm = ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
            temperature=0.2
        )
        
        # Compose the LCEL chain
        chain = self.prompt | llm | StrOutputParser()
        
        # Async invoke the chain
        return await chain.ainvoke({
            "message": message,
            "context": context,
            "tool_context": tool_context
        })
