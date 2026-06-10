import pytest
from app.modules.intents.classifier import IntentClassifier
from app.modules.intents.taxonomy import IntentTaxonomy

@pytest.mark.asyncio
async def test_intent_classification_balance():
    classifier = IntentClassifier()
    res = await classifier.classify_intent("Tôi muốn kiểm tra số dư ví khả dụng hiện tại của mình là bao nhiêu?")
    assert res.intent == IntentTaxonomy.BALANCE_INQUIRY.value
    assert res.confidence >= 0.8

@pytest.mark.asyncio
async def test_intent_classification_fees():
    classifier = IntentClassifier()
    res = await classifier.classify_intent("Chuyển tiền liên ngân hàng có bị mất phí duy trì hay không?")
    assert res.intent == IntentTaxonomy.FEE_INQUIRY.value

@pytest.mark.asyncio
async def test_intent_classification_limits():
    classifier = IntentClassifier()
    res = await classifier.classify_intent("Hạn mức tối đa giao dịch một ngày qua ví là bao nhiêu?")
    assert res.intent == IntentTaxonomy.LIMIT_INQUIRY.value

@pytest.mark.asyncio
async def test_intent_classification_fraud():
    classifier = IntentClassifier()
    res = await classifier.classify_intent("Tôi bị lừa đảo gạt tiền chuyển khoản cho người lạ giúp tôi với!")
    assert res.intent == IntentTaxonomy.FRAUD_OR_SCAM_REPORT.value

@pytest.mark.asyncio
async def test_intent_classification_security():
    classifier = IntentClassifier()
    res = await classifier.classify_intent("Tôi nghi ngờ bị lộ mã otp và mật khẩu ví VSmartPay")
    assert res.intent == IntentTaxonomy.ACCOUNT_SECURITY.value

@pytest.mark.asyncio
async def test_intent_classification_kyc():
    classifier = IntentClassifier()
    res = await classifier.classify_intent("Làm thế nào để xác minh danh tính tài khoản kyc ví?")
    assert res.intent == IntentTaxonomy.KYC_SUPPORT.value

@pytest.mark.asyncio
async def test_intent_classification_fallback():
    classifier = IntentClassifier()
    res = await classifier.classify_intent("Chào ngày mới")
    assert res.intent == IntentTaxonomy.FAQ_GENERAL.value
    # Handled via local fallback logic which outputs 0.5 confidence for this query
    assert res.confidence == 0.5

@pytest.mark.asyncio
async def test_intent_classification_bot_identity():
    classifier = IntentClassifier()
    res = await classifier.classify_intent("bạn là ai")
    assert res.intent == IntentTaxonomy.BOT_IDENTITY.value
    assert res.confidence >= 0.9
    
    res2 = await classifier.classify_intent("cho tôi hỏi bạn tên là gì?")
    assert res2.intent == IntentTaxonomy.BOT_IDENTITY.value
    assert res2.confidence >= 0.9
