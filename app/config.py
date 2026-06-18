from typing import List, Union
import json
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

    APP_NAME: str = "VSmartPay AI Support Agent"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # MongoDB
    MONGODB_URL: str
    DATABASE_NAME: str = "vsmartpay_support_agent"

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    BCRYPT_LOG_ROUNDS: int = 12

    # OpenAI & RAG Configs
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    VECTOR_STORE_PATH: str = "vector_store/faiss_index"
    MONGODB_VECTOR_INDEX_NAME: str = "vector_index"
    MONGODB_KEYWORD_INDEX_NAME: str = "keyword_index"
    TOP_K: int = 5
    USE_LANGGRAPH: bool = True
    VECTOR_STORE: str = "faiss"
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 100

    # Agent
    LLM_AGENT_ENABLED: bool = True
    LLM_AGENT_FALLBACK_TO_RULES: bool = True

    # Routing
    ROUTING_CONFIDENCE_THRESHOLD: float = 0.6
    ROUTING_HIGH_RISK_INTENTS: Union[str, List[str]] = ["ACCOUNT_SECURITY", "FRAUD_OR_SCAM_REPORT", "FAILED_TRANSACTION", "REFUND_OR_DISPUTE"]
    ROUTING_DIRECT_ESCALATION_INTENTS: Union[str, List[str]] = ["HUMAN_SUPPORT_REQUEST", "FRAUD_OR_SCAM_REPORT", "ACCOUNT_SECURITY", "REFUND_OR_DISPUTE"]

    @field_validator("ROUTING_HIGH_RISK_INTENTS", "ROUTING_DIRECT_ESCALATION_INTENTS", mode="before")
    @classmethod
    def parse_string_list(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("["):
                try:
                    return json.loads(v)
                except Exception:
                    return []
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    # API
    API_V1_STR: str = "/api/v1"

    # CORS
    BACKEND_CORS_ORIGINS: Union[str, List[str]] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, str) and v.startswith("["):
            try:
                return json.loads(v)
            except Exception:
                return []
        return v

    # LangSmith Configuration
    LANGSMITH_TRACING: bool = False
    LANGSMITH_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGSMITH_API_KEY: str | None = None
    LANGSMITH_PROJECT: str = "vsmartpay-ai-support-agent"

settings = Settings()

import os
if settings.LANGSMITH_TRACING:
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_ENDPOINT"] = settings.LANGSMITH_ENDPOINT
    if settings.LANGSMITH_API_KEY:
        os.environ["LANGSMITH_API_KEY"] = settings.LANGSMITH_API_KEY
    if settings.LANGSMITH_PROJECT:
        os.environ["LANGSMITH_PROJECT"] = settings.LANGSMITH_PROJECT
