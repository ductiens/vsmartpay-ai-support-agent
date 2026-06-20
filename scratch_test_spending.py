import asyncio
import os
import sys

sys.path.append(os.path.dirname(__file__))
sys.stdout.reconfigure(encoding='utf-8')  # type: ignore

from app.modules.intents.classifier import IntentClassifier
from app.core.nodes import tool_router_node
from app.core.state import SupportAgentState
from app.database import db_manager

async def test():
    await db_manager.connect()
    c = IntentClassifier()
    msgs = [
        "3 tháng nay tôi chi bao nhiêu vào ăn uống?",
        "Tôi đã tiêu bao nhiêu tiền xăng trong tháng qua?",
        "Tháng này tôi chi tiêu thế nào?",
        "Tuần vừa rồi tôi chuyển bao nhiêu tiền cho mục đích di chuyển?",
        "Năm ngoái tôi xài hết bao nhiêu tiền?"
    ]
    for msg in msgs:
        res = await c.classify_intent(msg)
        print(f"Message: {msg}")
        print(f"Intent: {res.intent} (conf: {res.confidence})")
        
        state = SupportAgentState(
            user_message=msg,
            intent=res.intent,
            user_id="test_user",
            kb_type="faq",
            agent_scope="general",
            draft_answer="",
            final_answer="",
            tool_calls=[],
            escalation_required=False,
            injection_detected=False,
            nodes_executed=[]
        )
        
        tool_res = await tool_router_node(state)
        print(f"Tool calls: {tool_res.get('tool_calls', [])}")
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(test())
