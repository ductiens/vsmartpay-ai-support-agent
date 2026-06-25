import json
import logging
from app.config import settings
from app.modules.intents.schema import IntentClassification
from app.modules.intents.taxonomy import IntentTaxonomy

logger = logging.getLogger(__name__)

class IntentClassifier:
    async def classify_intent(self, message: str) -> IntentClassification:
        """
        Classify user query into a precise intent.
        Uses heuristics first, and if not resolved, calls LLM for natural language classification.
        """
        msg_lower = message.lower().strip()
        
        # 1. Heuristics for direct/explicit commands or queries to ensure high confidence and speed
        
        # 0. Greetings / Chào hỏi xã giao
        greetings = ["hi", "hello", "xin chào", "chào bạn", "chào ad", "hi?", "hello?"]
        if msg_lower in greetings or any(msg_lower.startswith(g + " ") for g in greetings):
            return IntentClassification(intent=IntentTaxonomy.FAQ_GENERAL.value, confidence=0.95)
            
        # 0b. Bot identity query
        bot_identity_queries = [
            "bạn là ai", "ai đây", "may la ai", "mày là ai", "bạn tên gì", "bot là ai", 
            "ban la ai", "ten ban la gi", "tên bạn là gì", "introduce yourself", "giới thiệu bản thân"
        ]
        if msg_lower in bot_identity_queries or any(q in msg_lower for q in ["bạn là ai", "bạn tên là gì", "mày là ai"]):
            return IntentClassification(intent=IntentTaxonomy.BOT_IDENTITY.value, confidence=0.95)

        # 1. Human Support Requests
        if any(w in msg_lower for w in ["gặp nhân viên", "cskh", "tư vấn viên", "gặp tư vấn", "gặp hỗ trợ"]):
            return IntentClassification(intent=IntentTaxonomy.HUMAN_SUPPORT_REQUEST.value, confidence=0.95)
            
        # 2. Fees Inquiry
        if any(w in msg_lower for w in ["phí chuyển", "phí rút", "phí nạp", "biểu phí", "phí duy trì", "tốn phí", "thu phí", "phí bao nhiêu", "tính phí"]):
            return IntentClassification(intent=IntentTaxonomy.FEE_INQUIRY.value, confidence=0.95)
            
        # 3. Limits Inquiry
        if any(w in msg_lower for w in ["hạn mức", "limit"]):
            return IntentClassification(intent=IntentTaxonomy.LIMIT_INQUIRY.value, confidence=0.95)
            
        # 4. Transaction History
        if any(w in msg_lower for w in ["lịch sử", "gần đây", "history", "sao kê"]):
            return IntentClassification(intent=IntentTaxonomy.TRANSACTION_HISTORY.value, confidence=0.95)
            
        # 4b. Transaction Status
        if any(w in msg_lower for w in ["giao dịch", "mã giao dịch", "trạng thái"]):
            return IntentClassification(intent=IntentTaxonomy.TRANSACTION_STATUS.value, confidence=0.95)
            
        # 5. Balance Inquiry
        if any(w in msg_lower for w in ["số dư", "balance", "tài khoản còn bao nhiêu", "tôi còn bao nhiêu tiền"]):
            return IntentClassification(intent=IntentTaxonomy.BALANCE_INQUIRY.value, confidence=0.95)

        # 5b. Spending Statistics
        if any(w in msg_lower for w in ["chi tiêu", "chi bao nhiêu", "tiêu bao nhiêu", "thống kê chi", "tổng chi", "tiêu cho", "hết bao nhiêu", "đổ xăng", "đi taxi", "mua sắm", "tiền điện", "tiền nước"]):
            return IntentClassification(intent=IntentTaxonomy.SPENDING_STATISTICS.value, confidence=0.95)

        # 6. Fraud or Scam Report
        if any(w in msg_lower for w in ["lừa đảo", "scam", "bị gạt"]):
            return IntentClassification(intent=IntentTaxonomy.FRAUD_OR_SCAM_REPORT.value, confidence=0.95)

        # 7. Account Security
        if any(w in msg_lower for w in ["bị hack", "otp", "mật khẩu", "đổi mật khẩu", "pin", "khóa tài khoản"]):
            return IntentClassification(intent=IntentTaxonomy.ACCOUNT_SECURITY.value, confidence=0.95)

        # 8. KYC Support
        if any(w in msg_lower for w in ["kyc", "xác thực danh tính", "xác minh"]):
            return IntentClassification(intent=IntentTaxonomy.KYC_SUPPORT.value, confidence=0.95)

        # 9. Bank Linking
        if any(w in msg_lower for w in ["liên kết ngân hàng", "liên kết thẻ", "hủy liên kết"]):
            return IntentClassification(intent=IntentTaxonomy.BANK_LINKING.value, confidence=0.95)

        # 10. Failed Transaction
        if any(w in msg_lower for w in ["lỗi giao dịch", "thất bại", "không chuyển được", "bị treo"]):
            return IntentClassification(intent=IntentTaxonomy.FAILED_TRANSACTION.value, confidence=0.95)

        # 11. Promotions
        if any(w in msg_lower for w in ["khuyến mãi", "ưu đãi", "quà", "gift"]):
            return IntentClassification(intent=IntentTaxonomy.PROMOTION_INQUIRY.value, confidence=0.95)

        # 2. LLM Classify Intent for natural language
        api_key = settings.OPENAI_API_KEY
        if api_key and api_key != "your_openai_api_key_here":
            try:
                from openai import AsyncOpenAI
                from langsmith.wrappers import wrap_openai
                client = wrap_openai(AsyncOpenAI(api_key=api_key))
                
                # List of valid intents for prompt instruction
                intents_list = [enum.value for enum in IntentTaxonomy]
                
                system_instruction = (
                    "Bạn là chuyên gia phân loại ý định (intent classifier) cho trợ lý ảo của ví điện tử VSmartPay.\n"
                    "Nhiệm vụ của bạn là đọc tin nhắn của khách hàng và phân loại chính xác vào MỘT trong các nhóm ý định sau:\n"
                    f"{', '.join(intents_list)}\n\n"
                    "Các quy tắc đặc biệt:\n"
                    "- Nếu khách hàng hỏi về tiền còn bao nhiêu hiện tại hoặc kiểm tra số dư tài khoản -> BALANCE_INQUIRY\n"
                    "- Nếu khách hàng hỏi về thống kê chi tiêu, tổng số tiền đã tiêu, chi bao nhiêu tiền vào việc gì, hoặc hỏi số tiền cụ thể đã trả cho các dịch vụ (như tiền điện, tiền nước, tiền đổ xăng, đi taxi, mua sắm) trong 1 khoảng thời gian -> SPENDING_STATISTICS\n"
                    "- Nếu khách hàng hỏi về lịch sử giao dịch, tra cứu biến động số dư, xem sao kê -> TRANSACTION_HISTORY\n"
                    "- Nếu khách hàng hỏi han bot là ai, introduce, giới thiệu -> BOT_IDENTITY\n"
                    "- Nếu khách hàng chào hỏi xã giao thông thường -> FAQ_GENERAL\n"
                    "- Nếu tin nhắn chứa thông tin mông lung, không rõ ràng và không thể phân loại chắc chắn -> FAQ_GENERAL với confidence thấp\n"
                    "- Nếu tin nhắn không liên quan đến ví điện tử VSmartPay hoặc hoạt động tài chính -> OUT_OF_SCOPE\n"
                    "Trả về kết quả dưới định dạng JSON duy nhất:\n"
                    "{\n"
                    "  \"intent\": \"TÊN_Ý_ĐỊNH\",\n"
                    "  \"confidence\": float_từ_0.0_đến_1.0\n"
                    "}"
                )
                
                response = await client.chat.completions.create(
                    model=settings.OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": f"Tin nhắn khách hàng: \"{message}\"\nJSON kết quả:"}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.0
                )
                
                res_dict = json.loads(response.choices[0].message.content or "{}")
                intent_val = res_dict.get("intent")
                confidence_val = float(res_dict.get("confidence", 0.5))
                
                if intent_val in intents_list:
                    return IntentClassification(intent=intent_val, confidence=confidence_val)
                    
            except Exception as e:
                logger.error(f"LLM Intent classification failed: {e}")

        # Fallback to local rule-based heuristics logic if LLM failed
        # Basic check for partial matches as a softer backup
        if "chi tiêu" in msg_lower or "chi bao nhiêu" in msg_lower or "tiêu bao nhiêu" in msg_lower:
            return IntentClassification(intent=IntentTaxonomy.SPENDING_STATISTICS.value, confidence=0.8)
        if "số dư" in msg_lower or "còn bao nhiêu" in msg_lower:
            return IntentClassification(intent=IntentTaxonomy.BALANCE_INQUIRY.value, confidence=0.8)
        if "lịch sử" in msg_lower or "sao kê" in msg_lower:
            return IntentClassification(intent=IntentTaxonomy.TRANSACTION_HISTORY.value, confidence=0.8)
        if "phí" in msg_lower:
            return IntentClassification(intent=IntentTaxonomy.FEE_INQUIRY.value, confidence=0.8)
        if "hạn mức" in msg_lower:
            return IntentClassification(intent=IntentTaxonomy.LIMIT_INQUIRY.value, confidence=0.8)
        if "lừa đảo" in msg_lower or "bị lừa" in msg_lower or "mất tiền" in msg_lower:
            return IntentClassification(intent=IntentTaxonomy.FRAUD_OR_SCAM_REPORT.value, confidence=0.8)
        if "bị hack" in msg_lower or "lộ otp" in msg_lower:
            return IntentClassification(intent=IntentTaxonomy.ACCOUNT_SECURITY.value, confidence=0.8)
            
        return IntentClassification(intent=IntentTaxonomy.FAQ_GENERAL.value, confidence=0.5)
