import asyncio
from app.core.graph import graph
from app.config import settings

async def main():
    initial_state = {
        "session_id": "test",
        "user_id": "test",
        "user_message": "Cho mình hỏi số dư",
        "normalized_message": "cho mình hỏi số dư",
        "intent": "BALANCE_INQUIRY",
        "confidence": 0.9,
        "tool_calls": [],
        "nodes_executed": []
    }
    run_config = {"run_name": "test_stream"}
    async for event in graph.astream_events(initial_state, config=run_config, version="v2"):
        if event["event"] == "on_chat_model_stream":
            print(event["data"]["chunk"].content, end="", flush=True)
        elif event["event"] == "on_chain_end" and event["name"] == "test_stream":
            print("\n\nFINAL STATE:", event["data"]["output"])

if __name__ == "__main__":
    asyncio.run(main())
