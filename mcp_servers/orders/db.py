import asyncio
import random
from typing import Dict, List, Optional

class OrdersDB:
    def __init__(self):
        # Mock database structured as: {tenant_id: {order_id: order_details}}
        self.orders: Dict[str, Dict[str, dict]] = {
            "tenant_a": {
                "ord_101": {"id": "ord_101", "user_id": "cust_101", "amount": 150.00, "status": "delivered", "item": "Wireless Headphones"},
                "ord_102": {"id": "ord_102", "user_id": "cust_101", "amount": 1200.00, "status": "completed", "item": "V1 Gaming Laptop"},
                "ord_103": {"id": "ord_103", "user_id": "cust_102", "amount": 80.00, "status": "delivered", "item": "Phone Charger"},
                "ord_104": {"id": "ord_104", "user_id": "cust_103", "amount": 2500.00, "status": "completed", "item": "Smart TV OLED"},
            },
            "tenant_b": {
                "ord_201": {"id": "ord_201", "user_id": "cust_201", "amount": 350.00, "status": "delivered", "item": "Smart Watch"},
                "ord_202": {"id": "ord_202", "user_id": "cust_202", "amount": 1500.00, "status": "completed", "item": "Office Ergonomic Chair"},
            }
        }

    async def search_orders(self, tenant_id: str, user_id: Optional[str] = None) -> List[dict]:
        """Search orders in tenant, optionally filtered by user_id."""
        await asyncio.sleep(0.05)  # Simulate DB delay
        tenant_orders = self.orders.get(tenant_id, {})
        if user_id:
            return [o for o in tenant_orders.values() if o["user_id"] == user_id]
        return list(tenant_orders.values())

    async def get_order_details(self, tenant_id: str, order_id: str) -> Optional[dict]:
        """Get order details by order_id."""
        await asyncio.sleep(0.05)
        return self.orders.get(tenant_id, {}).get(order_id)

    async def refund_order(self, tenant_id: str, order_id: str, reason: str) -> dict:
        """Refund an order (update status)."""
        await asyncio.sleep(0.1)
        order = await self.get_order_details(tenant_id, order_id)
        if not order:
            return {"status": "error", "message": f"Order {order_id} not found."}
        if order["status"] == "refunded":
            return {"status": "error", "message": f"Order {order_id} is already refunded."}
        
        order["status"] = "refunded"
        order["refund_reason"] = reason
        return {"status": "success", "order": order}

    async def cancel_order(self, tenant_id: str, order_id: str, reason: str) -> dict:
        """Cancel an order (update status)."""
        await asyncio.sleep(0.1)
        order = await self.get_order_details(tenant_id, order_id)
        if not order:
            return {"status": "error", "message": f"Order {order_id} not found."}
        if order["status"] in ["cancelled", "refunded"]:
            return {"status": "error", "message": f"Order {order_id} cannot be cancelled (status: {order['status']})."}
        
        order["status"] = "cancelled"
        order["cancel_reason"] = reason
        return {"status": "success", "order": order}

orders_db = OrdersDB()
