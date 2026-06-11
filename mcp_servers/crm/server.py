import os
import json
import logging
from typing import Dict, Optional
from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("crm_mcp")

from db import crm_db

# Initialize FastMCP Server
mcp = FastMCP("crm_mcp", host="0.0.0.0", port=int(os.getenv("PORT", 8002)))

# --- Tools ---

@mcp.tool()
async def get_customer(tenant_id: str, customer_id: str) -> str:
    """Retrieve details for a customer.
    
    Args:
        tenant_id: The ID of the tenant.
        customer_id: The unique customer ID.
    """
    customer = await crm_db.get_customer(tenant_id, customer_id)
    if not customer:
        return json.dumps({"status": "not_found", "message": f"Customer {customer_id} not found."})
    return json.dumps(customer)

@mcp.tool()
async def update_customer(tenant_id: str, customer_id: str, email: Optional[str] = None, phone: Optional[str] = None) -> str:
    """Update contact information for a customer.
    
    Args:
        tenant_id: The ID of the tenant.
        customer_id: The unique customer ID.
        email: New email address.
        phone: New phone number.
    """
    updates = {}
    if email:
        updates["email"] = email
    if phone:
        updates["phone"] = phone
        
    result = await crm_db.update_customer(tenant_id, customer_id, updates)
    return json.dumps(result)

@mcp.tool()
async def customer_notes(tenant_id: str, customer_id: str, note: str) -> str:
    """Append a new note to the customer's profile.
    
    Args:
        tenant_id: The ID of the tenant.
        customer_id: The unique customer ID.
        note: The note content to append.
    """
    result = await crm_db.add_customer_note(tenant_id, customer_id, note)
    return json.dumps(result)

# --- Resources ---

@mcp.resource("crm://customer-profile/{customer_id}")
async def customer_profile(customer_id: str) -> str:
    """Get the core profile of a customer across tenants (support lookup)."""
    # Simply lookup across tenants for demo
    for tenant_id in ["tenant_a", "tenant_b"]:
        cust = await crm_db.get_customer(tenant_id, customer_id)
        if cust:
            return f"Customer Profile ({customer_id}):\nName: {cust['name']}\nEmail: {cust['email']}\nTier: {cust['tier']}\nNotes: {cust['notes']}"
    return f"Customer {customer_id} not found in any tenant."

@mcp.resource("crm://customer-history/{customer_id}")
async def customer_history(customer_id: str) -> str:
    """Get the transaction history overview of a customer."""
    for tenant_id in ["tenant_a", "tenant_b"]:
        cust = await crm_db.get_customer(tenant_id, customer_id)
        if cust:
            return f"Customer Order History ({customer_id}):\n" + "\n".join([f"- {h}" for h in cust['history']])
    return f"Customer {customer_id} not found."

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
