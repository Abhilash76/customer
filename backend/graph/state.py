from typing import TypedDict, Annotated, Sequence, Optional, List, Dict, Any
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_id: str
    tenant_id: str
    role: str
    token: str # JWT Token passed to MCP servers
    tool_calls: Optional[List[Dict[str, Any]]]
    tool_results: Optional[List[Dict[str, Any]]]
    approval_required: bool
    current_step: str
    final_answer: Optional[str]
    conversation_id: str
    
    # Internal variables for human in the loop
    pending_approval: Optional[Dict[str, Any]]
