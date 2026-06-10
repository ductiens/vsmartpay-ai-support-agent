from typing import List, Optional
from app.modules.rag.schema import DocumentChunk
from app.modules.rag.embeddings import EmbeddingService
from app.modules.rag.vector_store import VectorStoreService

# TODO: Uncomment the import and decorator below once the langsmith nested async bug is fixed
# from langsmith import traceable

class RAGRetriever:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStoreService()

    # @traceable(run_type="retriever")
    async def retrieve(
        self, 
        query: str, 
        top_k: int = 5,
        agent_scope: Optional[str] = None,
        kb_type: Optional[str] = None,
        category: Optional[str] = None,
        fallback: bool = True
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

        # 1. First attempt: Strict search with metadata filters
        search_results = await self.vector_store.hybrid_search(
            query=query,
            query_embedding=query_emb,
            top_k=top_k,
            filter_dict=filter_dict if filter_dict else None
        )
        
        # 2. Fallback attempt: If strict search yields no results AND filters were actually applied AND fallback is enabled,
        # search generally across all documents without filters.
        if not search_results and filter_dict and fallback:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(
                f"RAG: Strict search returned no results for query '{query}' using filters {filter_dict}. "
                "Triggering fallback search across all document chunks."
            )
            search_results = await self.vector_store.hybrid_search(
                query=query,
                query_embedding=query_emb,
                top_k=top_k,
                filter_dict=None
            )
        
        retrieved_chunks = []
        for chunk, score in search_results:
            chunk.score = float(score)
            retrieved_chunks.append(chunk)
            
        return retrieved_chunks
