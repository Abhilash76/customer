# mcp_servers/orders/db.py

> **Source:** `mcp_servers/orders/db.py`  
> **Purpose:** In-memory mock order database with tenant isolation — simulates a real order management system.

---

## Imports

| Import | Library | Why used |
|--------|---------|----------|
| `asyncio` | stdlib | Simulate async DB latency |
| `random` | stdlib | *(imported but unused)* |
| `Dict, List, Optional` | `typing` | Type hints |

---

## Class: `OrdersDB`

### Data structure

```python
self.orders: Dict[str, Dict[str, dict]]
# {tenant_id: {order_id: order_details}}
```

### Seed data

**tenant_a:**

| Order ID | Customer | Amount | Status | Item |
|----------|----------|--------|--------|------|
| `ord_101` | cust_101 | $150 | delivered | Wireless Headphones |
| `ord_102` | cust_101 | **$1,200** | completed | V1 Gaming Laptop |
| `ord_103` | cust_102 | $80 | delivered | Phone Charger |
| `ord_104` | cust_103 | **$2,500** | completed | Smart TV OLED |

**tenant_b:**

| Order ID | Customer | Amount | Status | Item |
|----------|----------|--------|--------|------|
| `ord_201` | cust_201 | $350 | delivered | Smart Watch |
| `ord_202` | cust_202 | **$1,500** | completed | Office Ergonomic Chair |

Orders > $1,000 trigger human-in-the-loop approval in the LangGraph agent.

---

### `search_orders(tenant_id, user_id=None) -> List[dict]`

**Returns:** Orders for tenant, optionally filtered by `user_id`  
Simulates 50ms DB delay.

---

### `get_order_details(tenant_id, order_id) -> Optional[dict]`

**Returns:** Order dict or `None` if not found / wrong tenant

---

### `refund_order(tenant_id, order_id, reason) -> dict`

**Returns:** `{"status": "success", "order": {...}}` or error

Sets `status = "refunded"`, adds `refund_reason`.

---

### `cancel_order(tenant_id, order_id, reason) -> dict`

**Returns:** Success or error (already cancelled/refunded)

Sets `status = "cancelled"`, adds `cancel_reason`.

---

## Singleton: `orders_db = OrdersDB()`

---

## MCP connection

```mermaid
flowchart LR
    TOOL["MCP tool handler"] --> DB["orders_db"]
    DB --> MEM["In-memory dict per tenant"]
```

MCP tools in `server.py` call these methods — the MCP server owns its data layer.

---

## MCP novice notes

This is a **mock database** for demo purposes. In production, `OrdersDB` would connect to a real database, and the MCP server would remain the single integration point for order operations.
