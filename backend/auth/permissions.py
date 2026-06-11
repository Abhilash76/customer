from typing import Set, Dict, List

# Map roles to permitted tool names
ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    "admin": {
        "search_orders_v1", "get_order_details_v1", "refund_order_v1", "cancel_order_v1",
        "get_customer", "update_customer", "customer_notes",
        "create_ticket", "search_ticket", "update_ticket"
    },
    "support": {
        "search_orders_v1", "get_order_details_v1",
        "get_customer",
        "create_ticket", "search_ticket"
    },
    "viewer": {
        "search_orders_v1", "get_order_details_v1",
        "get_customer",
        "search_ticket"
    }
}

def has_permission(role: str, tool_name: str) -> bool:
    """Check if the given role is allowed to call the specific tool."""
    allowed_tools = ROLE_PERMISSIONS.get(role, set())
    return tool_name in allowed_tools

def filter_permitted_tools(role: str, tools: List[dict]) -> List[dict]:
    """Filter a list of tool objects (from MCP) based on the user's role."""
    allowed = ROLE_PERMISSIONS.get(role, set())
    return [t for t in tools if t.get("name") in allowed]
