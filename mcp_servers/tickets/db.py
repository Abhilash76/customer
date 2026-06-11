import asyncio
import random
from typing import Dict, Optional, List

class TicketsDB:
    def __init__(self):
        # Mock database: {tenant_id: {ticket_id: ticket_data}}
        self.tickets: Dict[str, Dict[str, dict]] = {
            "tenant_a": {
                "tkt_1001": {"id": "tkt_1001", "customer_id": "cust_101", "subject": "Late delivery of ord_101", "status": "closed", "priority": "medium"},
                "tkt_1002": {"id": "tkt_1002", "customer_id": "cust_101", "subject": "Refund request for ord_102", "status": "open", "priority": "high"}
            },
            "tenant_b": {
                "tkt_2001": {"id": "tkt_2001", "customer_id": "cust_201", "subject": "Help setting up Smart Watch", "status": "open", "priority": "low"}
            }
        }

    async def create_ticket(self, tenant_id: str, customer_id: str, subject: str, priority: str) -> dict:
        await asyncio.sleep(0.05)
        ticket_id = f"tkt_{random.randint(1000, 9999)}"
        new_ticket = {
            "id": ticket_id,
            "customer_id": customer_id,
            "subject": subject,
            "status": "open",
            "priority": priority
        }
        if tenant_id not in self.tickets:
            self.tickets[tenant_id] = {}
        self.tickets[tenant_id][ticket_id] = new_ticket
        return new_ticket

    async def search_tickets(self, tenant_id: str, customer_id: Optional[str] = None) -> List[dict]:
        await asyncio.sleep(0.05)
        tenant_tickets = self.tickets.get(tenant_id, {})
        if customer_id:
            return [t for t in tenant_tickets.values() if t["customer_id"] == customer_id]
        return list(tenant_tickets.values())

    async def update_ticket(self, tenant_id: str, ticket_id: str, status: Optional[str] = None, priority: Optional[str] = None) -> dict:
        await asyncio.sleep(0.05)
        ticket = self.tickets.get(tenant_id, {}).get(ticket_id)
        if not ticket:
            return {"status": "error", "message": f"Ticket {ticket_id} not found."}
        
        if status:
            ticket["status"] = status
        if priority:
            ticket["priority"] = priority
            
        return {"status": "success", "ticket": ticket}

tickets_db = TicketsDB()
