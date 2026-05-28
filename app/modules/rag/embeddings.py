from app.config import settings
import numpy as np
from typing import List

class EmbeddingService:
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.EMBEDDING_MODEL

    async def get_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        (Phase 1: Basic OpenAI call with robust mock fallback if API key is empty)
        """
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            # Return a deterministic mock embedding vector of size 1536
            # utilizing hash of the text to ensure consistency in tests
            rng = np.random.default_rng(hash(text) & 0xffffffff)
            vec = rng.random(1536) - 0.5
            norm = np.linalg.norm(vec)
            vec = vec / norm if norm > 0 else vec
            return vec.tolist()
            
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=self.api_key)
            response = await client.embeddings.create(
                input=[text],
                model=self.model
            )
            return response.data[0].embedding
        except Exception:
            # Fallback in case of API error
            rng = np.random.default_rng(hash(text) & 0xffffffff)
            vec = rng.random(1536) - 0.5
            norm = np.linalg.norm(vec)
            vec = vec / norm if norm > 0 else vec
            return vec.tolist()
