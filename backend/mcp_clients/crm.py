import json
import logging
from typing import Dict, Any, Optional
from mcp_clients.base import BaseMCPClient
from db.redis import redis_cache
from config import settings

logger = logging.getLogger("backend.mcp_client.crm")

class CRMMCPClient(BaseMCPClient):
    def __init__(self):
        super().__init__(settings.CRM_MCP_URL, "crm_mcp")

    async def get_customer(self, tenant_id: str, customer_id: str) -> Dict[str, Any]:
        """Invoke get_customer with Redis caching."""
        cache_key = f"customer_cache:{tenant_id}:{customer_id}"
        
        # Check Cache
        cached = await redis_cache.get_cache(cache_key)
        if cached:
            logger.info(f"Redis Cache hit in backend client for customer {customer_id}")
            return cached

        # Call tool
        args = {"tenant_id": tenant_id, "customer_id": customer_id}
        res = await self.call_tool_with_retry("get_customer", args)
        
        if res["status"] == "success":
            try:
                customer_data = json.loads(res["content"])
                # Save to cache
                await redis_cache.set_cache(cache_key, customer_data, ttl=300)
                return customer_data
            except Exception as e:
                logger.error(f"Error parsing get_customer response: {e}")
                
        return res

    async def update_customer(self, tenant_id: str, customer_id: str, email: Optional[str] = None, phone: Optional[str] = None) -> Dict[str, Any]:
        await redis_cache.delete_cache(f"customer_cache:{tenant_id}:{customer_id}")
        args = {"tenant_id": tenant_id, "customer_id": customer_id}
        if email:
            args["email"] = email
        if phone:
            args["phone"] = phone
            
        res = await self.call_tool_with_retry("update_customer", args)
        if res["status"] == "success":
            return json.loads(res["content"])
        return res

    async def customer_notes(self, tenant_id: str, customer_id: str, note: str) -> Dict[str, Any]:
        await redis_cache.delete_cache(f"customer_cache:{tenant_id}:{customer_id}")
        args = {"tenant_id": tenant_id, "customer_id": customer_id, "note": note}
        res = await self.call_tool_with_retry("customer_notes", args)
        if res["status"] == "success":
            return json.loads(res["content"])
        return res

crm_mcp_client = CRMMCPClient()
