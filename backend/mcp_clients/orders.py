import json
import logging
from typing import Dict, Any, Optional
from mcp_clients.base import BaseMCPClient
from db.redis import redis_cache
from config import settings

logger = logging.getLogger("backend.mcp_client.orders")

class OrdersMCPClient(BaseMCPClient):
    def __init__(self):
        super().__init__(settings.ORDERS_MCP_URL, "orders_mcp")

    async def get_order_details(self, tenant_id: str, token: str, order_id: str) -> Dict[str, Any]:
        """Invoke get_order_details with Redis caching."""
        cache_key = f"order_cache:{tenant_id}:{order_id}"
        
        # Check Cache
        cached = await redis_cache.get_cache(cache_key)
        if cached:
            logger.info(f"Redis Cache hit in backend client for order {order_id}")
            return cached

        # Call tool
        args = {"tenant_id": tenant_id, "token": token, "order_id": order_id}
        res = await self.call_tool_with_retry("get_order_details_v1", args)
        
        if res["status"] == "success":
            try:
                order_data = json.loads(res["content"])
                # Save to cache
                await redis_cache.set_cache(cache_key, order_data, ttl=300)
                return order_data
            except Exception as e:
                logger.error(f"Error parsing order details response: {e}")
                
        return res
        
    async def search_orders(self, tenant_id: str, token: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        args = {"tenant_id": tenant_id, "token": token}
        if user_id:
            args["user_id"] = user_id
        res = await self.call_tool_with_retry("search_orders_v1", args)
        if res["status"] == "success":
            return json.loads(res["content"])
        return res

    async def refund_order(self, tenant_id: str, token: str, order_id: str, reason: str) -> Dict[str, Any]:
        # Invalidate Cache first or after
        await redis_cache.delete_cache(f"order_cache:{tenant_id}:{order_id}")
        args = {"tenant_id": tenant_id, "token": token, "order_id": order_id, "reason": reason}
        res = await self.call_tool_with_retry("refund_order_v1", args)
        if res["status"] == "success":
            return json.loads(res["content"])
        return res

    async def cancel_order(self, tenant_id: str, token: str, order_id: str, reason: str) -> Dict[str, Any]:
        await redis_cache.delete_cache(f"order_cache:{tenant_id}:{order_id}")
        args = {"tenant_id": tenant_id, "token": token, "order_id": order_id, "reason": reason}
        res = await self.call_tool_with_retry("cancel_order_v1", args)
        if res["status"] == "success":
            return json.loads(res["content"])
        return res

orders_mcp_client = OrdersMCPClient()
