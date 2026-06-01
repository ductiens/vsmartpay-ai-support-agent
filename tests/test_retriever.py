import pytest
from app.modules.rag.retriever import RAGRetriever
from app.modules.rag.vector_store import VectorStoreService
from unittest.mock import patch

@pytest.mark.asyncio
@patch("app.modules.rag.embeddings.EmbeddingService.get_embedding")
async def test_retriever_scope_limits(mock_get_emb):
    # Mock embedding return
    mock_get_emb.return_value = [0.01] * 1536
    
    retriever = RAGRetriever()
    res = await retriever.retrieve(
        query="Hạn mức một ngày",
        top_k=2,
        agent_scope="limits", # Scoped to limits
        kb_type="policy"
    )
    
    assert len(res) > 0
    # The seeded limits chunk has category "Hạn mức"
    assert res[0].metadata["category"] == "Hạn mức"
    assert res[0].metadata["kb_type"] == "policy"

@pytest.mark.asyncio
@patch("app.modules.rag.embeddings.EmbeddingService.get_embedding")
async def test_retriever_scope_security(mock_get_emb):
    mock_get_emb.return_value = [0.01] * 1536
    
    retriever = RAGRetriever()
    res = await retriever.retrieve(
        query="Nghi ngờ lừa đảo",
        top_k=2,
        agent_scope="security",
        kb_type="policy"
    )
    
    assert len(res) > 0
    # The seeded security chunk has category "Bảo mật"
    assert res[0].metadata["category"] == "Bảo mật"

@pytest.mark.asyncio
@patch("app.modules.rag.embeddings.EmbeddingService.get_embedding")
async def test_retriever_unmatched_scope(mock_get_emb):
    mock_get_emb.return_value = [0.01] * 1536
    
    retriever = RAGRetriever()
    # Non-existent scope
    res = await retriever.retrieve(
        query="Biểu phí",
        top_k=2,
        agent_scope="fees",
        kb_type="policy"
    )
    assert len(res) == 0
