from typing import List, Optional
from app.modules.rag.schema import DocumentChunk
from app.modules.rag.embeddings import EmbeddingService
from app.modules.rag.vector_store import VectorStoreService

class RAGRetriever:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStoreService()

    async def retrieve(
        self, 
        query: str, 
        top_k: int = 5,
        agent_scope: Optional[str] = None,
        kb_type: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[DocumentChunk]:
        """
        Embed user query and search vector store with dynamic scoping filters.
        """
        query_emb = await self.embedding_service.get_embedding(query)
        
        # Build standard MongoDB filters mapping
        filter_dict = {}
        if agent_scope:
            filter_dict["agent_scope"] = {"$eq": agent_scope}
        if kb_type:
            filter_dict["kb_type"] = {"$eq": kb_type}
        if category:
            filter_dict["category"] = {"$eq": category}

        search_results = await self.vector_store.search(
            query_embedding=query_emb,
            top_k=top_k,
            filter_dict=filter_dict if filter_dict else None
        )
        
        retrieved_chunks = []
        for chunk, score in search_results:
            chunk.score = float(score)
            retrieved_chunks.append(chunk)
            
        return retrieved_chunks
