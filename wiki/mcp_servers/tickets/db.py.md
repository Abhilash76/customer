# mcp_servers/tickets/db.py

> **Source:** `mcp_servers/tickets/db.py`  
> **Purpose:** In-memory mock support ticket database with tenant isolation.

---

## Imports

| Import | Library | Why used |
|--------|---------|----------|
| `asyncio` | stdlib | Simulate DB latency |
| `random` | stdlib | Generate random ticket IDs |
| `Dict, Optional, List` | `typing` | Type hints |

---

## Class: `TicketsDB`

### Seed data

**tenant_a:**
- `tkt_1001` — cust_101, "Late delivery of ord_101", closed, medium
- `tkt_1002` — cust_101, "Refund request for ord_102", open, high

**tenant_b:**
- `tkt_2001` — cust_201, "Help setting up Smart Watch", open, low

---

### `create_ticket(tenant_id, customer_id, subject, priority) -> dict`

**Returns:** New ticket dict with auto-generated `tkt_{1000-9999}` ID

Creates tenant bucket if missing.

---

### `search_tickets(tenant_id, customer_id=None) -> List[dict]`

**Returns:** Tickets for tenant, optionally filtered by customer

---

### `update_ticket(tenant_id, ticket_id, status=None, priority=None) -> dict`

**Returns:** `{"status": "success", "ticket": {...}}` or not-found error

---

## Singleton: `tickets_db = TicketsDB()`

---

## MCP connection

Only accessed through MCP tool handlers in `tickets/server.py`.

---

## MCP novice notes

`tkt_1002` ("Refund request for ord_102") pairs with the $1,200 order that triggers human approval — useful for demo scenarios where the agent creates or references existing tickets during refund workflows.
