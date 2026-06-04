import pytest
from app.modules.escalation.service import EscalationService

@pytest.mark.asyncio
async def test_escalation_security_intent():
    service = EscalationService()
    res = await service.evaluate_escalation(
        user_id="usr_01",
        last_message="Tài khoản ví của tôi nghi ngờ bị hack",
        intent="ACCOUNT_SECURITY",
        confidence=0.9
    )
    assert res.required is True
    assert res.priority == "HIGH"

@pytest.mark.asyncio
async def test_escalation_transaction_failed():
    service = EscalationService()
    res = await service.evaluate_escalation(
        user_id="usr_01",
        last_message="Tại sao giao dịch lại không thực hiện được?",
        intent="TRANSACTION_STATUS",
        confidence=0.9,
        transaction_status="FAILED"
    )
    assert res.required is True
    assert res.priority == "HIGH"

@pytest.mark.asyncio
async def test_escalation_low_confidence():
    service = EscalationService()
    res = await service.evaluate_escalation(
        user_id="usr_01",
        last_message="Một tin nhắn mông lung",
        intent="FAQ_GENERAL",
        confidence=0.4 # below 0.6 threshold
    )
    assert res.required is True
    assert res.priority == "LOW"

@pytest.mark.asyncio
async def test_escalation_context_insufficient():
    service = EscalationService()
    res = await service.evaluate_escalation(
        user_id="usr_01",
        last_message="Tôi muốn biết hạn mức của ví",
        intent="LIMIT_INQUIRY",
        confidence=0.9,
        context_insufficient=True # Insufficient chunks retrieved
    )
    assert res.required is True
    assert res.priority == "LOW"

@pytest.mark.asyncio
async def test_no_escalation_context_insufficient_for_normal_intent():
    service = EscalationService()
    res = await service.evaluate_escalation(
        user_id="usr_01",
        last_message="Tôi muốn biết chính sách bảo hiểm của đối tác ví",
        intent="FAQ_GENERAL",
        confidence=0.9,
        context_insufficient=True # Insufficient chunks retrieved
    )
    assert res.required is False

@pytest.mark.asyncio
async def test_escalation_out_of_scope():
    service = EscalationService()
    res = await service.evaluate_escalation(
        user_id="usr_01",
        last_message="Hướng dẫn tôi sửa chữa xe máy",
        intent="OUT_OF_SCOPE",
        confidence=0.9
    )
    assert res.required is True
    assert res.priority == "LOW"

@pytest.mark.asyncio
async def test_no_escalation_required():
    service = EscalationService()
    res = await service.evaluate_escalation(
        user_id="usr_01",
        last_message="Cho tôi hỏi về hạn mức của ví?",
        intent="LIMIT_INQUIRY",
        confidence=0.9,
        context_insufficient=False
    )
    assert res.required is False
