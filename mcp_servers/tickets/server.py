import os
import json
import logging
from typing import Optional, List
from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tickets_mcp")

from db import tickets_db

# Initialize FastMCP Server
mcp = FastMCP("tickets_mcp", host="0.0.0.0", port=int(os.getenv("PORT", 8003)))

# --- Tools ---

@mcp.tool()
async def create_ticket(tenant_id: str, customer_id: str, subject: str, priority: str = "medium") -> str:
    """Create a new support ticket.
    
    Args:
        tenant_id: The ID of the tenant.
        customer_id: The unique customer ID.
        subject: Brief explanation of the customer issue.
        priority: Priority of the ticket (low, medium, high, urgent).
    """
    ticket = await tickets_db.create_ticket(tenant_id, customer_id, subject, priority)
    return json.dumps(ticket)

@mcp.tool()
async def search_ticket(tenant_id: str, customer_id: Optional[str] = None) -> str:
    """Search for support tickets, optionally filtered by customer_id.
    
    Args:
        tenant_id: The ID of the tenant.
        customer_id: Optional customer ID to filter tickets.
    """
    tickets = await tickets_db.search_tickets(tenant_id, customer_id)
    return json.dumps(tickets)

@mcp.tool()
async def update_ticket(tenant_id: str, ticket_id: str, status: Optional[str] = None, priority: Optional[str] = None) -> str:
    """Update status or priority of a support ticket.
    
    Args:
        tenant_id: The ID of the tenant.
        ticket_id: The unique ticket ID.
        status: The new status (open, in_progress, closed).
        priority: The new priority (low, medium, high, urgent).
    """
    result = await tickets_db.update_ticket(tenant_id, ticket_id, status, priority)
    return json.dumps(result)

# --- Resources ---

@mcp.resource("tickets://templates")
async def ticket_templates() -> str:
    """Get templates for common support issues."""
    return json.dumps({
        "refund_request": {
            "subject": "Refund Request - Order [Order ID]",
            "body": "Customer is requesting a refund for Order [Order ID] due to [Reason]."
        },
        "shipping_delay": {
            "subject": "Shipping Delay Inquiry - Order [Order ID]",
            "body": "Customer reports that Order [Order ID] has not arrived. Expected delivery date was [Date]."
        },
        "technical_support": {
            "subject": "Technical Assistance - [Product]",
            "body": "Customer needs assistance with setting up or troubleshooting [Product]."
        }
    })

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
