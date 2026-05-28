from pydantic import BaseModel

class IntentClassification(BaseModel):
    intent: str
    confidence: float
