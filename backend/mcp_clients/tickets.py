import json
import logging
from typing import Dict, Any, Optional
from mcp_clients.base import BaseMCPClient
from config import settings

logger = logging.getLogger("backend.mcp_client.tickets")

class TicketsMCPClient(BaseMCPClient):
    def __init__(self):
        super().__init__(settings.TICKETS_MCP_URL, "tickets_mcp")

    async def create_ticket(self, tenant_id: str, customer_id: str, subject: str, priority: str = "medium") -> Dict[str, Any]:
        args = {"tenant_id": tenant_id, "customer_id": customer_id, "subject": subject, "priority": priority}
        res = await self.call_tool_with_retry("create_ticket", args)
        if res["status"] == "success":
            return json.loads(res["content"])
        return res

    async def search_ticket(self, tenant_id: str, customer_id: Optional[str] = None) -> Dict[str, Any]:
        args = {"tenant_id": tenant_id}
        if customer_id:
            args["customer_id"] = customer_id
        res = await self.call_tool_with_retry("search_ticket", args)
        if res["status"] == "success":
            return json.loads(res["content"])
        return res

    async def update_ticket(self, tenant_id: str, ticket_id: str, status: Optional[str] = None, priority: Optional[str] = None) -> Dict[str, Any]:
        args = {"tenant_id": tenant_id, "ticket_id": ticket_id}
        if status:
            args["status"] = status
        if priority:
            args["priority"] = priority
            
        res = await self.call_tool_with_retry("update_ticket", args)
        if res["status"] == "success":
            return json.loads(res["content"])
        return res

tickets_mcp_client = TicketsMCPClient()
