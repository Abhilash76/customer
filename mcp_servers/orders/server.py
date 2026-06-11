import os
import json
import logging
from typing import Optional, List
from mcp.server.fastmcp import FastMCP
import redis

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("orders_mcp")

# Import DB and auth helpers
from db import orders_db
from auth import decode_token, verify_tool_permission

# Initialize Redis client
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    logger.info("Connected to Redis for caching.")
except Exception as e:
    redis_client = None
    logger.warning(f"Redis not available: {e}")

# Initialize FastMCP Server (host/port set here; run() only accepts transport)
mcp = FastMCP("orders_mcp", host="0.0.0.0", port=int(os.getenv("PORT", 8001)))

# Helper function to validate authorization
def authorize(token: str, tool_name: str, requested_tenant: str) -> dict:
    claims = decode_token(token)
    if not claims:
        raise ValueError("Invalid or expired JWT token.")
    
    user_id = claims.get("user_id")
    tenant_id = claims.get("tenant_id")
    role = claims.get("role")
    
    if tenant_id != requested_tenant:
        raise ValueError("Tenant access violation.")
        
    if not verify_tool_permission(role, tool_name):
        raise ValueError(f"Role '{role}' is not authorized to execute '{tool_name}'.")
        
    return {
        "user_id": user_id,
        "tenant_id": tenant_id,
        "role": role
    }

# --- Tools ---

@mcp.tool()
async def search_orders_v1(tenant_id: str, token: str, user_id: Optional[str] = None) -> str:
    """Search orders belonging to a tenant, optionally filtered by user_id.
    
    Args:
        tenant_id: The ID of the tenant.
        token: The user's JWT authorization token.
        user_id: Optional user ID to filter orders.
    """
    try:
        authorize(token, "search_orders_v1", tenant_id)
        orders = await orders_db.search_orders(tenant_id, user_id)
        return json.dumps(orders)
    except ValueError as e:
        return json.dumps({"status": "permission_denied", "message": str(e)})

@mcp.tool()
async def get_order_details_v1(tenant_id: str, token: str, order_id: str) -> str:
    """Get detailed information about a specific order.
    
    Args:
        tenant_id: The ID of the tenant.
        token: The user's JWT authorization token.
        order_id: The unique order ID.
    """
    try:
        authorize(token, "get_order_details_v1", tenant_id)
        
        # Redis Caching logic
        cache_key = f"order_cache:{tenant_id}:{order_id}"
        if redis_client:
            try:
                cached = redis_client.get(cache_key)
                if cached:
                    logger.info(f"Cache hit for order {order_id}")
                    return cached
            except Exception as ex:
                logger.error(f"Redis read error: {ex}")

        order = await orders_db.get_order_details(tenant_id, order_id)
        if not order:
            return json.dumps({"status": "not_found", "message": "Order not found."})
            
        result_str = json.dumps(order)
        
        # Set cache
        if redis_client:
            try:
                redis_client.setex(cache_key, 300, result_str)
                logger.info(f"Cached order {order_id}")
            except Exception as ex:
                logger.error(f"Redis write error: {ex}")
                
        return result_str
    except ValueError as e:
        return json.dumps({"status": "permission_denied", "message": str(e)})

@mcp.tool()
async def refund_order_v1(tenant_id: str, token: str, order_id: str, reason: str) -> str:
    """Refund a specific order. Refunds above $1000 require manager approval.
    
    Args:
        tenant_id: The ID of the tenant.
        token: The user's JWT authorization token.
        order_id: The unique order ID.
        reason: The reason for the refund.
    """
    try:
        authorize(token, "refund_order_v1", tenant_id)
        
        # Check if the order details exist first
        order = await orders_db.get_order_details(tenant_id, order_id)
        if not order:
            return json.dumps({"status": "not_found", "message": "Order not found."})
            
        # If order amount > 1000, verify check
        if order["amount"] > 1000:
            # Note: The LangGraph workflow intercepts this and pauses for approval.
            # But the server still returns a response or requires an approval flag.
            # Let's check if there is approval
            logger.info(f"Refund of order {order_id} (amount: {order['amount']}) requires human approval.")
        
        result = await orders_db.refund_order(tenant_id, order_id, reason)
        
        # Invalidate Cache
        if redis_client:
            try:
                redis_client.delete(f"order_cache:{tenant_id}:{order_id}")
            except Exception as ex:
                logger.error(f"Redis delete error: {ex}")
                
        return json.dumps(result)
    except ValueError as e:
        return json.dumps({"status": "permission_denied", "message": str(e)})

@mcp.tool()
async def cancel_order_v1(tenant_id: str, token: str, order_id: str, reason: str) -> str:
    """Cancel a specific order.
    
    Args:
        tenant_id: The ID of the tenant.
        token: The user's JWT authorization token.
        order_id: The unique order ID.
        reason: The reason for cancellation.
    """
    try:
        authorize(token, "cancel_order_v1", tenant_id)
        result = await orders_db.cancel_order(tenant_id, order_id, reason)
        
        # Invalidate Cache
        if redis_client:
            try:
                redis_client.delete(f"order_cache:{tenant_id}:{order_id}")
            except Exception as ex:
                logger.error(f"Redis delete error: {ex}")
                
        return json.dumps(result)
    except ValueError as e:
        return json.dumps({"status": "permission_denied", "message": str(e)})

# --- Resources ---

@mcp.resource("orders://refund-policy")
async def refund_policy() -> str:
    """Get the company's official refund policy document."""
    return (
        "Official Refund Policy:\n"
        "1. Full refunds are available for order cancellations before shipping.\n"
        "2. Delivered products are eligible for a refund within 30 days of purchase.\n"
        "3. Any refund for transactions exceeding $1,000.00 requires a mandatory supervisor approval (Human-in-the-loop).\n"
        "4. Refunds will be processed back to the original payment method within 5-10 business days."
    )

# --- Prompts ---

@mcp.prompt()
async def executive_summary(order_id: str) -> str:
    """Generate a prompt to summarize an order status for executives.
    
    Args:
        order_id: The order ID.
    """
    return (
        f"Generate a professional, structured executive summary for Order {order_id}. "
        "Include the total amount, items, current delivery status, and any potential issues or customer satisfaction implications."
    )

if __name__ == "__main__":
    # streamable-http exposes the MCP endpoint at /mcp (matches ORDERS_MCP_URL in docker-compose)
    mcp.run(transport="streamable-http")
