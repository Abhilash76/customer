import json
import logging
from typing import Optional, Dict, Any, List
from langchain_core.tools import tool
from mcp_clients.orders import orders_mcp_client
from mcp_clients.crm import crm_mcp_client
from mcp_clients.tickets import tickets_mcp_client

logger = logging.getLogger("backend.graph.tools")

# --- Orders Tools ---

@tool
async def search_orders_v1(tenant_id: str, token: str, user_id: Optional[str] = None) -> str:
    """Search for orders. Always returns a JSON list of orders."""
    res = await orders_mcp_client.search_orders(tenant_id, token, user_id)
    return json.dumps(res)

@tool
async def get_order_details_v1(tenant_id: str, token: str, order_id: str) -> str:
    """Get detailed information about a specific order by order_id."""
    res = await orders_mcp_client.get_order_details(tenant_id, token, order_id)
    return json.dumps(res)

@tool
async def refund_order_v1(tenant_id: str, token: str, order_id: str, reason: str) -> str:
    """Request a refund for an order. Refunds > $1000 require human approval."""
    res = await orders_mcp_client.refund_order(tenant_id, token, order_id, reason)
    return json.dumps(res)

@tool
async def cancel_order_v1(tenant_id: str, token: str, order_id: str, reason: str) -> str:
    """Cancel an order before shipment."""
    res = await orders_mcp_client.cancel_order(tenant_id, token, order_id, reason)
    return json.dumps(res)

# --- CRM Tools ---

@tool
async def get_customer(tenant_id: str, customer_id: str) -> str:
    """Retrieve details for a customer."""
    res = await crm_mcp_client.get_customer(tenant_id, customer_id)
    return json.dumps(res)

@tool
async def update_customer(tenant_id: str, customer_id: str, email: Optional[str] = None, phone: Optional[str] = None) -> str:
    """Update contact info for a customer."""
    res = await crm_mcp_client.update_customer(tenant_id, customer_id, email, phone)
    return json.dumps(res)

@tool
async def customer_notes(tenant_id: str, customer_id: str, note: str) -> str:
    """Append notes to customer profile."""
    res = await crm_mcp_client.customer_notes(tenant_id, customer_id, note)
    return json.dumps(res)

# --- Ticket Tools ---

@tool
async def create_ticket(tenant_id: str, customer_id: str, subject: str, priority: str = "medium") -> str:
    """Create a new support ticket."""
    res = await tickets_mcp_client.create_ticket(tenant_id, customer_id, subject, priority)
    return json.dumps(res)

@tool
async def search_ticket(tenant_id: str, customer_id: Optional[str] = None) -> str:
    """Search for support tickets."""
    res = await tickets_mcp_client.search_ticket(tenant_id, customer_id)
    return json.dumps(res)

@tool
async def update_ticket(tenant_id: str, ticket_id: str, status: Optional[str] = None, priority: Optional[str] = None) -> str:
    """Update support ticket status or priority."""
    res = await tickets_mcp_client.update_ticket(tenant_id, ticket_id, status, priority)
    return json.dumps(res)

# Master list of all tools
ALL_TOOLS = [
    search_orders_v1, get_order_details_v1, refund_order_v1, cancel_order_v1,
    get_customer, update_customer, customer_notes,
    create_ticket, search_ticket, update_ticket
]

def get_tools_for_role(role: str) -> List[Any]:
    """Get LangChain tools filtered by role."""
    from auth.permissions import ROLE_PERMISSIONS
    allowed_names = ROLE_PERMISSIONS.get(role, set())
    return [t for t in ALL_TOOLS if t.name in allowed_names]
