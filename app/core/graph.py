import time
import logging
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END

from app.core.state import SupportAgentState
from app.core.nodes import (
    injection_guard_node,
    intent_agent_node,
    tool_router_node,
    rag_agent_node,
    grounding_guard_node,
    confidence_agent_node,
    escalation_agent_node,
    clarification_agent_node,
    final_answer_node
)
from app.modules.chat.schema import ChatRequest, ChatResponse, ChatSource, EscalationDetail
from app.modules.chat.repository import ChatRepository
from app.common.utils import generate_id, now_utc

logger = logging.getLogger(__name__)

# 1. Define conditional routing logic
def route_decision(state: SupportAgentState) -> Literal["escalation", "clarification", "final"]:
    """
    Python rules only routing decision based on state parameters:
    - injection_detected = true -> escalation_agent
    - escalation_required = true -> escalation_agent
    - grounded = false -> clarification_agent
    - confidence < 0.6 -> clarification_agent or escalation_agent
    - else -> final_answer
    """
    injection_detected = state.get("injection_detected", False)
    escalation_required = state.get("escalation_required", False)
    grounded = state.get("grounded", True)
    confidence = state.get("confidence", 1.0)
    intent = state.get("intent", "FAQ_GENERAL")
    
    if injection_detected:
        return "escalation"
        
    if escalation_required:
        return "escalation"
        
    if not grounded:
        return "clarification"
        
    if confidence < 0.6:
        # Sensitive security, fraud, or transaction related inquiries get escalated
        sensitive_intents = ["BALANCE_INQUIRY", "TRANSACTION_STATUS", "FEE_INQUIRY", "ACCOUNT_SECURITY", "FRAUD_OR_SCAM_REPORT"]
        if intent in sensitive_intents:
            return "escalation"
        return "clarification"
        
    return "final"

def route_after_intent(state: SupportAgentState) -> Literal["escalation", "tool_router"]:
    """
    Directly route to escalation_agent if prompt injection or direct escalation intent is detected.
    """
    if state.get("injection_detected", False) or state.get("escalation_required", False):
        return "escalation"
        
    intent = state.get("intent", "FAQ_GENERAL")
    direct_escalation_intents = ["HUMAN_SUPPORT_REQUEST", "FRAUD_OR_SCAM_REPORT", "ACCOUNT_SECURITY", "REFUND_OR_DISPUTE"]
    if intent in direct_escalation_intents:
        return "escalation"
        
    return "tool_router"

# 2. Build the workflow StateGraph
workflow = StateGraph(SupportAgentState)

# Add all agents and node wrappers
workflow.add_node("injection_guard", injection_guard_node)
workflow.add_node("intent_agent", intent_agent_node)
workflow.add_node("tool_router", tool_router_node)
workflow.add_node("rag_agent", rag_agent_node)
workflow.add_node("grounding_guard", grounding_guard_node)
workflow.add_node("confidence_agent", confidence_agent_node)
workflow.add_node("escalation_agent", escalation_agent_node)
workflow.add_node("clarification_agent", clarification_agent_node)
workflow.add_node("final_answer_node", final_answer_node)

# Connect the nodes in linear flow
workflow.set_entry_point("injection_guard")
workflow.add_edge("injection_guard", "intent_agent")

workflow.add_conditional_edges(
    "intent_agent",
    route_after_intent,
    {
        "escalation": "escalation_agent",
        "tool_router": "tool_router"
    }
)

workflow.add_edge("tool_router", "rag_agent")
workflow.add_edge("rag_agent", "grounding_guard")
workflow.add_edge("grounding_guard", "confidence_agent")

# Connect confidence_agent to routing decisions
workflow.add_conditional_edges(
    "confidence_agent",
    route_decision,
    {
        "escalation": "escalation_agent",
        "clarification": "clarification_agent",
        "final": "final_answer_node"
    }
)

# Connect endpoints to END
workflow.add_edge("escalation_agent", END)
workflow.add_edge("clarification_agent", END)
workflow.add_edge("final_answer_node", END)

# Compile the graph
graph = workflow.compile()


# 3. Main runner function to execute LangGraph in /chat endpoint
async def execute_graph(request: ChatRequest) -> ChatResponse:
    """
    Executes the compiled LangGraph workflow from user request to ChatResponse,
    logging the session and user/assistant messages in MongoDB.
    """
    start_time = time.time()
    request_id = f"req_{generate_id()}"
    repository = ChatRepository()
    
    # Step 1: Log session and user message in MongoDB
    await repository.log_session(request.session_id, request.user_id)
    await repository.log_message(
        session_id=request.session_id,
        role="user",
        content=request.message
    )
    
    # Step 2: Initialize state parameters
    initial_state = {
        "session_id": request.session_id,
        "user_id": request.user_id,
        "user_message": request.message,
        "normalized_message": request.message.strip(),
        "intent": "FAQ_GENERAL",
        "retrieved_chunks": [],
        "retrieval_score": 0.0,
        "tool_calls": [],
        "tool_results": [],
        "draft_answer": "",
        "final_answer": "",
        "confidence": 0.5,
        "grounded": True,
        "injection_detected": False,
        "escalation_required": False,
        "escalation_reason": "",
        "sources": [],
        "metadata": {},
        "doc_ids": [],
        "kb_type": "",
        "agent_scope": "",
        "retrieval_filter": {},
        "nodes_executed": []
    }
    
    # Step 3: Run compiled graph
    final_state = await graph.ainvoke(initial_state)
    
    # Extract output fields
    answer = final_state.get("final_answer", "")
    intent = final_state.get("intent", "FAQ_GENERAL")
    confidence = final_state.get("confidence", 0.5)
    sources_data = final_state.get("sources", [])
    tool_calls = final_state.get("tool_calls", [])
    nodes_executed = final_state.get("nodes_executed", [])
    
    # Format sources into ChatSource list
    sources = [
        ChatSource(
            doc_id=s.get("doc_id", "unknown"),
            chunk_id=s.get("chunk_id", ""),
            title=s.get("title", ""),
            score=s.get("score", 0.0)
        ) for s in sources_data
    ]
    
    # Extract escalation details
    escalation_required = final_state.get("escalation_required", False)
    escalation_reason = final_state.get("escalation_reason", None)
    
    # Retrieve priority from metadata
    meta = final_state.get("metadata", {})
    esc_meta = meta.get("escalation", {})
    priority = esc_meta.get("priority", "MEDIUM") if escalation_required else None
    
    # Step 4: Log assistant message in MongoDB
    # Convert ChatSource models to dictionary list for DB
    db_sources = [
        {
            "doc_id": s.doc_id,
            "chunk_id": s.chunk_id,
            "title": s.title,
            "score": s.score
        } for s in sources
    ]
    await repository.log_message(
        session_id=request.session_id,
        role="assistant",
        content=answer,
        intent=intent,
        sources=db_sources
    )

    if escalation_required:
        # Transition chat session status to WAITING_HUMAN
        await repository.update_session_status(request.session_id, "WAITING_HUMAN")

    # Logging & Tracing
    latency_ms = (time.time() - start_time) * 1000
    retrieved_chunks = final_state.get("retrieved_chunks", [])
    trace_chunks = [
        {
            "doc_id": getattr(c, "metadata", {}).get("source", "unknown") if hasattr(c, "metadata") else c.get("metadata", {}).get("source", "unknown"),
            "chunk_id": getattr(c, "id", "") if hasattr(c, "id") else c.get("id", ""),
            "title": getattr(c, "metadata", {}).get("category", "Tài liệu VSmartPay") if hasattr(c, "metadata") else c.get("metadata", {}).get("category", "Tài liệu VSmartPay"),
            "score": float(getattr(c, "score", 0.0)) if hasattr(c, "score") else float(c.get("score", 0.0))
        }
        for c in retrieved_chunks
    ]
    trace_doc = {
        "request_id": request_id,
        "session_id": request.session_id,
        "user_id": request.user_id,
        "user_message": request.message,
        "intent": intent,
        "confidence": confidence,
        "tool_calls": tool_calls,
        "retrieved_chunks": trace_chunks,
        "nodes_executed": nodes_executed,
        "latency_ms": latency_ms,
        "timestamp": now_utc()
    }
    await repository.log_agent_trace(trace_doc)

    logger.info(
        f"[LANGGRAPH TRACE] request_id={request_id} | session_id={request.session_id} | "
        f"intent={intent} (conf={confidence:.2f}) | "
        f"tools_called={[tc['tool_name'] for tc in tool_calls]} | "
        f"nodes_executed={nodes_executed} | latency={latency_ms:.1f}ms"
    )
    
    return ChatResponse(
        answer=answer,
        intent=intent,
        confidence=confidence,
        sources=sources,
        tool_calls=tool_calls,
        escalation=EscalationDetail(
            required=escalation_required,
            reason=escalation_reason if escalation_reason else None,
            priority=priority
        )
    )
