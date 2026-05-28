from typing import List, Dict, Any, Optional
from app.config import settings
from app.modules.rag.retriever import RAGRetriever

class RAGService:
    def __init__(self):
        self.retriever = RAGRetriever()
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.OPENAI_MODEL

    async def get_context_for_query(
        self, 
        query: str, 
        top_k: int = 5,
        agent_scope: Optional[str] = None,
        kb_type: Optional[str] = None,
        category: Optional[str] = None
    ) -> str:
        """
        Retrieve relevant document chunks and format them as a combined context string with dynamic filters.
        """
        chunks = await self.retriever.retrieve(
            query=query, 
            top_k=top_k,
            agent_scope=agent_scope,
            kb_type=kb_type,
            category=category
        )
        context_parts = []
        for c in chunks:
            source = c.metadata.get("source", "unknown")
            cat = c.metadata.get("category", "General")
            context_parts.append(
                f"### Nguồn: {source} ({cat})\n"
                f"Nội dung: {c.text}"
            )
        return "\n\n".join(context_parts)

    async def answer_query(
        self, 
        query: str,
        agent_scope: Optional[str] = None,
        kb_type: Optional[str] = None,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve chunks and generate an answer using OpenAI API with scoping.
        """
        chunks = await self.retriever.retrieve(
            query=query, 
            top_k=settings.TOP_K,
            agent_scope=agent_scope,
            kb_type=kb_type,
            category=category
        )
        context = "\n".join([c.text for c in chunks])
        
        sources = [c.metadata.get("source", "unknown") for c in chunks]
        sources = list(set(sources)) # Unique list
        
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            # Return static mock response
            return {
                "answer": f"Dựa trên tài liệu hướng dẫn VSmartPay: {chunks[0].text if chunks else 'Hệ thống đang bảo trì.'}",
                "sources": sources
            }
            
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=self.api_key)
            prompt = f"Sử dụng thông tin dưới đây để trả lời câu hỏi của người dùng:\n\nThông tin:\n{context}\n\nCâu hỏi: {query}"
            
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Bạn là nhân viên hỗ trợ khách hàng của ví điện tử VSmartPay."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            return {
                "answer": response.choices[0].message.content,
                "sources": sources
            }
        except Exception as e:
            return {
                "answer": f"Đã xảy ra lỗi khi gọi LLM: {str(e)}. Phản hồi tạm thời dựa trên tài liệu: {chunks[0].text if chunks else ''}",
                "sources": sources
            }
