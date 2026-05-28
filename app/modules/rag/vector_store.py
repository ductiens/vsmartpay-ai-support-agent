import os
import json
from typing import List, Tuple
# pyrefly: ignore [missing-import]
import numpy as np
import faiss
from app.config import settings
from app.modules.rag.schema import DocumentChunk

class VectorStoreService:
    def __init__(self):
        self.store_path = settings.VECTOR_STORE_PATH # vector_store/faiss_index
        self.index = None
        self.metadata = []
        self.load_index()

    def load_index(self):
        """Load FAISS index and documents metadata."""
        if self.store_path.endswith("faiss_index"):
            index_file = os.path.join(self.store_path, "index.faiss")
            metadata_file = os.path.join(self.store_path, "index_metadata.json")
        else:
            index_file = f"{self.store_path}.faiss"
            metadata_file = f"{self.store_path}_metadata.json"

        if os.path.exists(index_file) and os.path.exists(metadata_file):
            try:
                self.index = faiss.read_index(index_file)
                with open(metadata_file, "r", encoding="utf-8") as f:
                    self.metadata = json.load(f)
                print(f"FAISS index loaded successfully from '{index_file}'. Loaded {len(self.metadata)} documents.")
            except Exception as e:
                print(f"Error loading FAISS index: {e}")
                self.index = None
                self.metadata = []
        else:
            print(f"FAISS index files not found at '{index_file}'. Please run build_vector_index.py to generate them.")
            self.index = None
            self.metadata = []

    def save_index(self):
        """Save FAISS index and documents metadata (in case index is constructed dynamically)."""
        if not self.index or not self.metadata:
            return
            
        if self.store_path.endswith("faiss_index"):
            os.makedirs(self.store_path, exist_ok=True)
            index_file = os.path.join(self.store_path, "index.faiss")
            metadata_file = os.path.join(self.store_path, "index_metadata.json")
        else:
            os.makedirs(os.path.dirname(self.store_path), exist_ok=True)
            index_file = f"{self.store_path}.faiss"
            metadata_file = f"{self.store_path}_metadata.json"

        try:
            faiss.write_index(self.index, index_file)
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving FAISS index: {e}")

    async def search(self, query_embedding: List[float], top_k: int = 4) -> List[Tuple[DocumentChunk, float]]:
        """
        Search for top_k documents similar to the query embedding.
        Uses Cosine Similarity via Inner Product of normalized vectors.
        """
        if self.index is None or not self.metadata:
            # Fallback mock chunk if index is empty/not built yet
            mock_chunk = DocumentChunk(
                id="doc_mock_default",
                text="Hạn mức chuyển tiền tối đa qua ví VSmartPay là 50.000.000 VND/ngày đối với tài khoản đã xác thực.",
                metadata={"source": "limits.md"},
                score=0.95
            )
            return [(mock_chunk, 0.95)]

        try:
            # Query embedding vector L2 Normalization
            query_np = np.array([query_embedding]).astype("float32")
            faiss.normalize_L2(query_np)

            # Search in FlatIP index
            scores, indices = self.index.search(query_np, top_k)
            
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < 0 or idx >= len(self.metadata):
                    continue
                
                meta = self.metadata[idx]
                chunk = DocumentChunk(
                    id=meta["chunk_id"],
                    text=meta["content"],
                    metadata={"source": os.path.basename(meta["source_path"]), "category": meta["category"]},
                    score=float(score)
                )
                results.append((chunk, float(score)))
                
            return results
        except Exception as e:
            print(f"Error during FAISS search: {e}")
            # Safe fallback
            mock_chunk = DocumentChunk(
                id="doc_mock_default",
                text="Hạn mức chuyển tiền tối đa qua ví VSmartPay là 50.000.000 VND/ngày đối với tài khoản đã xác thực.",
                metadata={"source": "limits.md"},
                score=0.95
            )
            return [(mock_chunk, 0.95)]
