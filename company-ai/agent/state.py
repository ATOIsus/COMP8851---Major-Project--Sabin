from typing import TypedDict, Optional, List, Dict, Any


class AgentState(TypedDict, total=False):
    email: dict
    reasoning: Optional[str]
    extracted: Optional[dict]
    tool_call: Optional[dict]
    tool_result: Optional[dict]
    final_response: Optional[str]
    tool_history: List[Dict[str, Any]]
    execution_id: Optional[str]
