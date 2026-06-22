import re
from typing import Dict, Any, cast
from app.core.state import SupportAgentState
from app.agents.injection_guard import check_injection
from app.agents.intent_agent import run_intent_agent
from app.agents.rag_agent import run_rag_agent
from app.agents.grounding_guard import run_grounding_guard
from app.agents.confidence_agent import run_confidence_agent
from app.agents.escalation_agent import run_escalation_agent
from app.agents.clarification_agent import run_clarification_agent
from app.agents.query_decomposition_agent import run_query_decomposition_agent
# Node Wrappers
async def injection_guard_node(state: SupportAgentState) -> Dict[str, Any]:
    res = check_injection(state)
    nodes = list(state.get("nodes_executed", []))
    nodes.append("injection_guard")
    res["nodes_executed"] = nodes
    return res

async def intent_agent_node(state: SupportAgentState) -> Dict[str, Any]:
    if state.get("injection_detected"):
        return {}
    res = await run_intent_agent(cast(Dict[str, Any], state))
    nodes = list(state.get("nodes_executed", []))
    nodes.append("intent_agent")
    res["nodes_executed"] = nodes
    return res

async def tool_router_node(state: SupportAgentState) -> Dict[str, Any]:
    """
    Check if the intent is transaction-related.
    If so, call the appropriate mock wallet tools and populate tool_calls.
    If not, proceed without calling tools.
    """
    if state.get("injection_detected"):
        return {}
        
    intent = state.get("intent", "FAQ_GENERAL")
    user_message = state.get("user_message", "") or ""
    user_id = state.get("user_id", "")
    
    tool_calls = list(state.get("tool_calls", []))
    
    # 1. BALANCE_INQUIRY → call check_balance
    if intent == "BALANCE_INQUIRY":
        from app.modules.tools.financial_tools import check_balance
        balance_data = await check_balance(user_id)
        tool_calls.append({
            "tool_name": "check_balance",
            "arguments": {"user_id": user_id},
            "result": balance_data
        })
        
    # 2. TRANSACTION_HISTORY → call get_transaction_history
    elif intent == "TRANSACTION_HISTORY":
        from app.modules.tools.financial_tools import get_transaction_history
        txn_history = await get_transaction_history(user_id)
        tool_calls.append({
            "tool_name": "get_transaction_history",
            "arguments": {"user_id": user_id},
            "result": txn_history
        })

    # 3. TRANSACTION_STATUS → extract transaction_id, call get_transaction_status
    elif intent == "TRANSACTION_STATUS":
        # Extract transaction ID (e.g. txn_001, txn_uuid_v7) using regex
        match = re.search(r"\b(txn_[0-9a-fA-F\-]+|tx_[0-9a-fA-F\-]+)\b", user_message, re.IGNORECASE)
        transaction_id = match.group(1) if match else None
        
        from app.modules.tools.financial_tools import get_transaction_status
        if transaction_id:
            txn_data = await get_transaction_status(transaction_id, user_id)
            tool_calls.append({
                "tool_name": "get_transaction_status",
                "arguments": {"transaction_id": transaction_id},
                "result": txn_data or {"error": f"Giao dịch {transaction_id} không tồn tại."}
            })
        else:
            tool_calls.append({
                "tool_name": "get_transaction_status",
                "arguments": {"transaction_id": None},
                "result": {"error": "Không tìm thấy mã giao dịch trong tin nhắn."}
            })
            
    # 4. FEE_INQUIRY → extract transaction_type & amount, call get_fee
    elif intent == "FEE_INQUIRY":
        msg_lower = user_message.lower()
        transaction_type = "TRANSFER"
        if "rút" in msg_lower or "withdraw" in msg_lower:
            transaction_type = "WITHDRAWAL"
        elif "nạp" in msg_lower or "deposit" in msg_lower:
            transaction_type = "DEPOSIT"
            
        # Default amount is 500,000 VND, else parse from message
        amount = 500000
        k_match = re.search(r"(\d+(?:\.\d+)?)\s*k\b", msg_lower)
        if k_match:
            amount = int(float(k_match.group(1)) * 100) if '.' in k_match.group(1) else int(k_match.group(1)) * 1000
        else:
            m_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:tr triệu|triệu|tr)\b", msg_lower)
            if m_match:
                amount = int(float(m_match.group(1)) * 1000000)
            else:
                nums = re.findall(r"\b\d+(?:[\.,]\d+)*\b", user_message)
                for num in nums:
                    cleaned = num.replace(".", "").replace(",", "")
                    val = int(cleaned)
                    if val > 1000:
                        amount = val
                        break
                        
        from app.modules.tools.financial_tools import get_fee
        fee_data = get_fee(transaction_type, amount)
        tool_calls.append({
            "tool_name": "get_fee",
            "arguments": {"transaction_type": transaction_type, "amount": amount},
            "result": fee_data
        })
        
    # 5. SPENDING_STATISTICS → extract months & category, call get_spending_statistics_tool
    elif intent == "SPENDING_STATISTICS":
        msg_lower = user_message.lower()
        
        # Extract timeframe
        months = 1
        if "năm" in msg_lower:
            months = 12
        else:
            month_match = re.search(r"(\d+)\s*tháng", msg_lower)
            if month_match:
                months = int(month_match.group(1))
            else:
                if "tuần" in msg_lower:
                    months = 1
        if months > 12:
            months = 12

        # Extract category mapping based on typical Vietnamese terms
        known_categories = {
            "ăn uống": "Ăn uống", "ăn": "Ăn uống", "ăn trưa": "Ăn uống", "ăn sáng": "Ăn uống", "ăn tối": "Ăn uống", "nhà hàng": "Ăn uống", "cà phê": "Ăn uống", "cafe": "Ăn uống",
            "di chuyển": "Di chuyển", "đi lại": "Di chuyển", "grab": "Di chuyển", "taxi": "Di chuyển",
            "xăng": "Xăng xe", "xăng xe": "Xăng xe", "đổ xăng": "Xăng xe",
            "mua sắm": "Mua sắm", "shopee": "Mua sắm", "quần áo": "Mua sắm", "siêu thị": "Mua sắm",
            "giải trí": "Giải trí", "xem phim": "Giải trí", "chơi game": "Giải trí",
            "hóa đơn": "Thanh toán hóa đơn", "tiền điện": "Thanh toán hóa đơn", "tiền nước": "Thanh toán hóa đơn", "tiền mạng": "Thanh toán hóa đơn"
        }
        
        detected_category = None
        for key, val in known_categories.items():
            if re.search(r"\b" + re.escape(key) + r"\b", msg_lower):
                detected_category = val
                break
                
        from app.modules.tools.financial_tools import get_spending_statistics_tool
        stats_data = await get_spending_statistics_tool(user_id, months, detected_category)
        
        tool_calls.append({
            "tool_name": "get_spending_statistics",
            "arguments": {"user_id": user_id, "months": months, "category": detected_category},
            "result": stats_data
        })

    nodes = list(state.get("nodes_executed", []))
    nodes.append("tool_router")
    return {
        "tool_calls": tool_calls,
        "nodes_executed": nodes
    }

async def query_decomposition_node(state: SupportAgentState) -> Dict[str, Any]:
    if state.get("injection_detected"):
        return {}
    res = await run_query_decomposition_agent(cast(Dict[str, Any], state))
    nodes = list(state.get("nodes_executed", []))
    nodes.append("query_decomposition_node")
    res["nodes_executed"] = nodes
    return res

async def rag_agent_node(state: SupportAgentState) -> Dict[str, Any]:
    if state.get("injection_detected"):
        return {}
    res = await run_rag_agent(cast(Dict[str, Any], state))
    nodes = list(state.get("nodes_executed", []))
    nodes.append("rag_agent")
    res["nodes_executed"] = nodes
    return res

async def grounding_guard_node(state: SupportAgentState) -> Dict[str, Any]:
    if state.get("injection_detected"):
        return {}
    res = await run_grounding_guard(cast(Dict[str, Any], state))
    nodes = list(state.get("nodes_executed", []))
    nodes.append("grounding_guard")
    res["nodes_executed"] = nodes
    return res

async def confidence_agent_node(state: SupportAgentState) -> Dict[str, Any]:
    if state.get("injection_detected"):
        return {}
    res = await run_confidence_agent(cast(Dict[str, Any], state))
    nodes = list(state.get("nodes_executed", []))
    nodes.append("confidence_agent")
    res["nodes_executed"] = nodes
    return res

async def escalation_agent_node(state: SupportAgentState) -> Dict[str, Any]:
    res = await run_escalation_agent(cast(Dict[str, Any], state))
    nodes = list(state.get("nodes_executed", []))
    nodes.append("escalation_agent")
    res["nodes_executed"] = nodes
    return res

async def clarification_agent_node(state: SupportAgentState) -> Dict[str, Any]:
    res = await run_clarification_agent(cast(Dict[str, Any], state))
    nodes = list(state.get("nodes_executed", []))
    nodes.append("clarification_agent")
    res["nodes_executed"] = nodes
    return res

async def final_answer_node(state: SupportAgentState) -> Dict[str, Any]:
    """
    Wrap up node: simply assign draft_answer to final_answer.
    """
    draft_answer = state.get("draft_answer", "")
    nodes = list(state.get("nodes_executed", []))
    nodes.append("final_answer_node")
    return {
        "final_answer": draft_answer,
        "nodes_executed": nodes
    }
