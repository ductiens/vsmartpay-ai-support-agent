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
        Routes to FAISS search if VECTOR_STORE settings config is set to 'faiss'.
        Otherwise, attempts MongoDB Atlas $vectorSearch aggregate pipeline first,
        and falls back to client-side cosine similarity calculation if aggregate fails.
        """
        if getattr(settings, "VECTOR_STORE", "atlas").lower() == "faiss":
            return await self._search_faiss(query_embedding, top_k, filter_dict)

        col = self.collection
        if col is None:
            return []

        # 1. MongoDB Atlas Vector Search Pipeline
        pipeline: List[Dict[str, Dict[str, Any]]] = [
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

    def _load_faiss_index(self):
        if hasattr(self, "_faiss_index") and getattr(self, "_faiss_index") is not None:
            return self._faiss_index, self._faiss_metadata

        import json
        import os
        try:
            import faiss
        except ImportError:
            print("Error: faiss-cpu package is not installed. Please run pip install faiss-cpu.")
            self._faiss_index = None
            self._faiss_metadata = []
            return None, []

        vector_store_dir = settings.VECTOR_STORE_PATH
        if vector_store_dir.endswith("faiss_index"):
            index_file = os.path.join(vector_store_dir, "index.faiss")
            metadata_file = os.path.join(vector_store_dir, "index_metadata.json")
        else:
            index_file = f"{vector_store_dir}.faiss"
            metadata_file = f"{vector_store_dir}_metadata.json"

        if os.path.exists(index_file) and os.path.exists(metadata_file):
            try:
                self._faiss_index = faiss.read_index(index_file)
                with open(metadata_file, "r", encoding="utf-8") as f:
                    self._faiss_metadata = json.load(f)
                return self._faiss_index, self._faiss_metadata
            except Exception as e:
                print(f"Error loading FAISS index: {e}")
        
        self._faiss_index = None
        self._faiss_metadata = []
        return None, []

    async def _search_faiss(
        self, 
        query_embedding: List[float], 
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[DocumentChunk, float]]:
        import numpy as np
        try:
            import faiss
        except ImportError:
            return []

        index, metadata = self._load_faiss_index()
        if not index or not metadata:
            print("Warning: FAISS index or metadata not found or empty. Returning empty search results.")
            return []

        # Convert query_embedding to numpy float32
        query_np = np.array([query_embedding]).astype("float32")
        faiss.normalize_L2(query_np)

        # Search in FAISS
        scores, indices = index.search(query_np, top_k * 4) # Fetch more to allow filter filtering
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(metadata):
                continue
            item = metadata[idx]
            
            doc_id = item.get("doc_id", "")
            category = item.get("category", "")
            
            # Infer kb_type and agent_scope based on doc_id and category
            kb_type = "faq"
            agent_scope = "general"
            if "limit" in doc_id.lower() or "limit" in category.lower():
                kb_type = "policy"
                agent_scope = "limits"
            elif "fee" in doc_id.lower() or "fee" in category.lower():
                kb_type = "policy"
                agent_scope = "fees"
            elif "security" in doc_id.lower() or "security" in category.lower():
                kb_type = "policy"
                agent_scope = "security"
            elif "transfer" in doc_id.lower() or "transfer" in category.lower():
                kb_type = "faq"
                agent_scope = "transfer"
                
            # Perform metadata filtering
            if filter_dict:
                matched = True
                for k, val in filter_dict.items():
                    expected_val = val.get("$eq") if isinstance(val, dict) and "$eq" in val else val
                    actual_val = None
                    if k == "agent_scope":
                        actual_val = agent_scope
                    elif k == "kb_type":
                        actual_val = kb_type
                    elif k == "category":
                        actual_val = category
                    elif k == "doc_id" or k == "file_name":
                        actual_val = doc_id
                        
                    if actual_val != expected_val:
                        matched = False
                        break
                if not matched:
                    continue
                    
            chunk = DocumentChunk(
                id=item.get("chunk_id", ""),
                text=item.get("content", ""),
                metadata={
                    "source": doc_id,
                    "category": category,
                    "page": item.get("page", 1),
                    "heading": item.get("heading", ""),
                    "agent_scope": agent_scope,
                    "kb_type": kb_type,
                    "language": "vi"
                },
                score=float(score)
            )
            results.append((chunk, float(score)))
            
        return results[:top_k]

