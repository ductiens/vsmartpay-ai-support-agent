import os
from typing import List, Tuple, Dict, Any, Optional
import numpy as np
from app.config import settings
from app.database import get_db
from app.modules.rag.schema import DocumentChunk

class VectorStoreService:
    def __init__(self):
        self.index_name = settings.MONGODB_VECTOR_INDEX_NAME

    @property
    def collection(self):
        db = get_db()
        if db is not None:
            return db["knowledge_chunks"]
        return None

    async def ensure_vector_search_index(self):
        """
        Attempt to create a search index on Atlas.
        Fails silently with warning on local/non-Atlas MongoDB deployments.
        """
        col = self.collection
        if col is None:
            return
            
        try:
            if hasattr(col, "create_search_index"):
                # Standard KNN vector index configuration
                index_definition = {
                    "mappings": {
                        "dynamic": True,
                        "fields": {
                            "embedding": {
                                "type": "knnVector",
                                "dimensions": 1536,
                                "similarity": "cosine"
                            }
                        }
                    }
                }
                await col.create_search_index(
                    definition=index_definition,
                    name=self.index_name
                )
                print(f"MongoDB Vector Search index '{self.index_name}' successfully created or verified.")
        except Exception as e:
            # Atlas Search Index creation is only supported on MongoDB Atlas.
            # Local MongoDB community instances will raise an exception; we log and pass.
            print(f"Warning: MongoDB Atlas Search index creation skipped or failed: {e}. Local fallback search will be used if needed.")

    async def save_index(self):
        """No-op for MongoDB Vector Search as chunks are saved directly to MongoDB."""
        pass

    async def load_index(self):
        """No-op for MongoDB Vector Search."""
        pass

    async def add_chunks(self, chunks: List[Dict[str, Any]]):
        """Insert knowledge chunks directly into MongoDB knowledge_chunks collection."""
        col = self.collection
        if col is not None and chunks:
            await col.insert_many(chunks)

    async def delete_chunks_by_doc_id(self, doc_id: str):
        """Delete all chunks belonging to a specific doc_id."""
        col = self.collection
        if col is not None:
            await col.delete_many({"doc_id": doc_id})

    async def search(
        self, 
        query_embedding: List[float], 
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[DocumentChunk, float]]:
        """
        Perform vector similarity search.
        Attempts MongoDB Atlas $vectorSearch aggregate pipeline first.
        Falls back to client-side cosine similarity calculation if aggregate fails or is unsupported.
        """
        col = self.collection
        if col is None:
            return []

        # 1. MongoDB Atlas Vector Search Pipeline
        pipeline = [
            {
                "$vectorSearch": {
                    "index": self.index_name,
                    "path": "embedding",
                    "queryVector": query_embedding,
                    "numCandidates": 100,
                    "limit": top_k
                }
            }
        ]

        # Inject filters into $vectorSearch if present
        if filter_dict:
            pipeline[0]["$vectorSearch"]["filter"] = filter_dict

        try:
            cursor = col.aggregate(pipeline)
            results = []
            async for doc in cursor:
                # Atlas vectorSearch returns results ordered by score.
                # In MongoDB, the similarity score is represented by a metadata score or the distance.
                # MongoDB Atlas search results in aggregate can obtain a search score.
                score = doc.get("$vectorSearchScore", 1.0)
                
                chunk = DocumentChunk(
                    id=doc.get("chunk_id", ""),
                    text=doc.get("content", ""),
                    metadata={
                        "source": doc.get("file_name", ""),
                        "category": doc.get("category", ""),
                        "page": doc.get("page"),
                        "heading": doc.get("heading"),
                        "agent_scope": doc.get("agent_scope"),
                        "kb_type": doc.get("kb_type"),
                        "language": doc.get("language")
                    },
                    score=score
                )
                results.append((chunk, score))
                
            if results:
                return results[:top_k]
                
        except Exception as e:
            # If $vectorSearch is unsupported (e.g. running local MongoDB Community Edition),
            # log the warning and proceed to manual fallback calculation.
            print(f"Atlas $vectorSearch failed or is unsupported on this environment: {e}. Falling back to manual search.")

        # 2. Local Fallback Search using manual Cosine Similarity
        return await self._fallback_manual_search(query_embedding, top_k, filter_dict)

    async def _fallback_manual_search(
        self, 
        query_embedding: List[float], 
        top_k: int, 
        filter_dict: Optional[Dict[str, Any]]
    ) -> List[Tuple[DocumentChunk, float]]:
        col = self.collection
        if col is None:
            return []

        # Parse MongoDB Match filter criteria to apply local filtering
        query_criteria = {}
        if filter_dict:
            for key, val in filter_dict.items():
                if isinstance(val, dict) and "$eq" in val:
                    query_criteria[key] = val["$eq"]
                else:
                    query_criteria[key] = val

        # Fetch matching chunks
        cursor = col.find(query_criteria)
        all_docs = []
        async for doc in cursor:
            all_docs.append(doc)

        if not all_docs:
            return []

        # Calculate cosine similarity manually using numpy
        query_vector = np.array(query_embedding).astype("float32")
        query_norm = np.linalg.norm(query_vector)

        search_results = []
        for doc in all_docs:
            doc_emb = doc.get("embedding")
            if not doc_emb or len(doc_emb) != len(query_embedding):
                continue
                
            doc_vector = np.array(doc_emb).astype("float32")
            doc_norm = np.linalg.norm(doc_vector)
            
            if query_norm == 0 or doc_norm == 0:
                similarity = 0.0
            else:
                similarity = float(np.dot(query_vector, doc_vector) / (query_norm * doc_norm))

            chunk = DocumentChunk(
                id=doc.get("chunk_id", ""),
                text=doc.get("content", ""),
                metadata={
                    "source": doc.get("file_name", ""),
                    "category": doc.get("category", ""),
                    "page": doc.get("page"),
                    "heading": doc.get("heading"),
                    "agent_scope": doc.get("agent_scope"),
                    "kb_type": doc.get("kb_type"),
                    "language": doc.get("language")
                },
                score=similarity
            )
            search_results.append((chunk, similarity))

        # Sort descending by similarity score
        search_results.sort(key=lambda x: x[1], reverse=True)
        return search_results[:top_k]
