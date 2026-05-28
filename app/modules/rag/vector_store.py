import os
from typing import List, Dict, Any, Tuple
from app.config import settings
from app.modules.rag.schema import DocumentChunk

class VectorStoreService:
    def __init__(self):
        self.store_path = settings.VECTOR_STORE_PATH
        self.documents: Dict[str, DocumentChunk] = {}
        # In actual phase, FAISS index will be loaded here
        self.faiss_index = None

    def save_index(self):
        """Save FAISS index and documents metadata."""
        pass

    def load_index(self):
        """Load FAISS index and documents metadata."""
        pass

    async def add_documents(self, chunks: List[DocumentChunk], embeddings: List[List[float]]):
        """Add document chunks and their embeddings to the store."""
        for chunk in chunks:
            self.documents[chunk.id] = chunk

    async def search(self, query_embedding: List[float], top_k: int = 4) -> List[Tuple[DocumentChunk, float]]:
        """
        Search for top_k documents similar to the query embedding.
        (Phase 1: Return available mock documents or empty list)
        """
        results = []
        # Return mock elements if no index exists
        for i, chunk in enumerate(list(self.documents.values())[:top_k]):
            results.append((chunk, 1.0 - (i * 0.1)))
            
        if not results:
            # Fallback mock chunk
            mock_chunk = DocumentChunk(
                id="doc_mock_default",
                text="Hạn mức chuyển tiền tối đa qua ví VSmartPay là 50.000.000 VND/ngày đối với tài khoản đã xác thực.",
                metadata={"source": "limits.md"},
                score=0.95
            )
            results.append((mock_chunk, 0.95))
            
        return results
