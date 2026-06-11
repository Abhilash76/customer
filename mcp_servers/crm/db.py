import asyncio
from typing import Dict, Optional, List

class CRMDB:
    def __init__(self):
        # Mock CRM database: {tenant_id: {customer_id: customer_data}}
        self.customers: Dict[str, Dict[str, dict]] = {
            "tenant_a": {
                "cust_101": {
                    "id": "cust_101",
                    "name": "Alice Johnson",
                    "email": "alice@gmail.com",
                    "phone": "555-0199",
                    "tier": "gold",
                    "notes": "Prefers email contact. Loyal customer since 2024.",
                    "history": ["Purchased Wireless Headphones (ord_101)", "Purchased Gaming Laptop (ord_102)"]
                },
                "cust_102": {
                    "id": "cust_102",
                    "name": "Bob Smith",
                    "email": "bob@gmail.com",
                    "phone": "555-0144",
                    "tier": "silver",
                    "notes": "Prefers text notifications.",
                    "history": ["Purchased Phone Charger (ord_103)"]
                },
                "cust_103": {
                    "id": "cust_103",
                    "name": "Charlie Brown",
                    "email": "charlie@gmail.com",
                    "phone": "555-0188",
                    "tier": "platinum",
                    "notes": "High-value corporate customer.",
                    "history": ["Purchased Smart TV OLED (ord_104)"]
                }
            },
            "tenant_b": {
                "cust_201": {
                    "id": "cust_201",
                    "name": "David Miller",
                    "email": "david@gmail.com",
                    "phone": "555-0211",
                    "tier": "bronze",
                    "notes": "New user.",
                    "history": ["Purchased Smart Watch (ord_201)"]
                },
                "cust_202": {
                    "id": "cust_202",
                    "name": "Emily Watson",
                    "email": "emily@gmail.com",
                    "phone": "555-0222",
                    "tier": "gold",
                    "notes": "Frequent buyer of home-office furniture.",
                    "history": ["Purchased Office Ergonomic Chair (ord_202)"]
                }
            }
        }

    async def get_customer(self, tenant_id: str, customer_id: str) -> Optional[dict]:
        await asyncio.sleep(0.05)
        return self.customers.get(tenant_id, {}).get(customer_id)

    async def update_customer(self, tenant_id: str, customer_id: str, updates: dict) -> dict:
        await asyncio.sleep(0.1)
        customer = await self.get_customer(tenant_id, customer_id)
        if not customer:
            return {"status": "error", "message": f"Customer {customer_id} not found."}
        
        for key, value in updates.items():
            if key in ["name", "email", "phone", "tier"]:
                customer[key] = value
        return {"status": "success", "customer": customer}

    async def add_customer_note(self, tenant_id: str, customer_id: str, note: str) -> dict:
        await asyncio.sleep(0.05)
        customer = await self.get_customer(tenant_id, customer_id)
        if not customer:
            return {"status": "error", "message": f"Customer {customer_id} not found."}
        
        customer["notes"] = customer.get("notes", "") + f"\nUpdate: {note}"
        return {"status": "success", "customer": customer}

crm_db = CRMDB()
