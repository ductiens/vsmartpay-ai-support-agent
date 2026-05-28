from pydantic import BaseModel
from typing import Dict, Any

class DocumentChunk(BaseModel):
    id: str
    text: str
    metadata: Dict[str, Any]
    score: float = 0.0
