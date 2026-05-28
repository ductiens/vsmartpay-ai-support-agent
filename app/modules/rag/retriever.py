from typing import List
from app.modules.rag.schema import DocumentChunk
from app.modules.rag.embeddings import EmbeddingService
from app.modules.rag.vector_store import VectorStoreService

class RAGRetriever:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStoreService()

    async def retrieve(self, query: str, top_k: int = 4) -> List[DocumentChunk]:
        """
        Embed user query and search vector store.
        """
        query_emb = await self.embedding_service.get_embedding(query)
        search_results = await self.vector_store.search(query_emb, top_k)
        
        retrieved_chunks = []
        for chunk, score in search_results:
            chunk.score = float(score)
            retrieved_chunks.append(chunk)
            
        return retrieved_chunks
