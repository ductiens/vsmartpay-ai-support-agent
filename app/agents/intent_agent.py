from app.modules.intents.classifier import IntentClassifier

async def run_intent_agent(state) -> dict:
    """
    Classify user message intent and determine the search boundaries (kb_type, agent_scope).
    """
    user_message = state.get("user_message", "") or ""
    
    # Run original classifier
    classifier = IntentClassifier()
    intent_info = await classifier.classify_intent(user_message)
    
    intent = intent_info.intent
    confidence = intent_info.confidence
    
    # Establish dynamic knowledge base boundaries based on intent
    kb_type = "faq"
    agent_scope = "general"
    
    if intent == "FEE_INQUIRY":
        kb_type = "policy"
        agent_scope = "fees"
    elif intent == "LIMIT_INQUIRY":
        kb_type = "policy"
        agent_scope = "limits"
    elif intent in ["ACCOUNT_SECURITY", "FRAUD_OR_SCAM_REPORT"]:
        kb_type = "policy"
        agent_scope = "security"
    elif intent == "TRANSFER_GUIDE":
        kb_type = "faq"
        agent_scope = "transfer"
        
    return {
        "intent": intent,
        "confidence": confidence,
        "kb_type": kb_type,
        "agent_scope": agent_scope,
        "normalized_message": user_message.strip()
    }
