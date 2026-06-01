import pytest
from app.agents.grounding_guard import run_grounding_guard
from app.modules.rag.schema import DocumentChunk

@pytest.mark.asyncio
async def test_grounding_guard_transaction_intent():
    state = {
        "intent": "BALANCE_INQUIRY",
        "draft_answer": "Số dư ví khả dụng của bạn là 2.500.000 VND.",
        "retrieved_chunks": []
    }
    res = await run_grounding_guard(state)
    assert res["grounded"] is True

@pytest.mark.asyncio
async def test_grounding_guard_no_chunks():
    state = {
        "intent": "LIMIT_INQUIRY",
        "draft_answer": "Hạn mức tối đa là 50 triệu.",
        "retrieved_chunks": [] # Empty chunks for knowledge intent
    }
    res = await run_grounding_guard(state)
    assert res["grounded"] is False

@pytest.mark.asyncio
async def test_grounding_guard_fallback_grounded():
    from app.config import settings
    original_key = settings.OPENAI_API_KEY
    settings.OPENAI_API_KEY = ""
    try:
        state = {
            "intent": "LIMIT_INQUIRY",
            "draft_answer": "Hạn mức tối đa là 50 triệu đối với tài khoản KYC.",
            "retrieved_chunks": [
                DocumentChunk(
                    id="chk_01",
                    text="Hạn mức tối đa là 50 triệu đối với tài khoản KYC.",
                    metadata={"source": "limits.md", "category": "Hạn mức"},
                    score=0.9
                )
            ]
        }
        res = await run_grounding_guard(state)
        assert res["grounded"] is True
    finally:
        settings.OPENAI_API_KEY = original_key


@pytest.mark.asyncio
async def test_grounding_guard_fallback_not_grounded():
    from app.config import settings
    original_key = settings.OPENAI_API_KEY
    settings.OPENAI_API_KEY = ""
    try:
        state = {
            "intent": "LIMIT_INQUIRY",
            "draft_answer": "Xin lỗi, tôi chưa tìm thấy tài liệu tương ứng.",
            "retrieved_chunks": [
                DocumentChunk(
                    id="chk_01",
                    text="Hạn mức tối đa là 50 triệu đối với tài khoản KYC.",
                    metadata={"source": "limits.md", "category": "Hạn mức"},
                    score=0.9
                )
            ]
        }
        res = await run_grounding_guard(state)
        assert res["grounded"] is False
    finally:
        settings.OPENAI_API_KEY = original_key
