from typing import TypedDict, List, Dict, Any, Optional

class SupportAgentState(TypedDict, total=False):
    """
    State representing the context of a customer support session 
    as it flows through the multi-agent graph.
    """
    session_id: str
    user_id: str
    user_message: str
    normalized_message: str
    intent: str
    retrieved_chunks: List[Any]
    retrieval_score: float
    tool_calls: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    draft_answer: str
    final_answer: str
    confidence: float
    grounded: bool
    injection_detected: bool
    escalation_required: bool
    escalation_reason: str
    sources: List[Any]
    metadata: Dict[str, Any]
    doc_ids: List[str]
    streaming_queue: Any
    kb_type: str
    agent_scope: str
    retrieval_filter: Dict[str, Any]
    nodes_executed: List[str]
