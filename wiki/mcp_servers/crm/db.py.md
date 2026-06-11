# mcp_servers/crm/db.py

> **Source:** `mcp_servers/crm/db.py`  
> **Purpose:** In-memory mock CRM database with per-tenant customer records.

---

## Imports

| Import | Library | Why used |
|--------|---------|----------|
| `asyncio` | stdlib | Simulate DB latency |
| `Dict, Optional, List` | `typing` | Type hints |

---

## Class: `CRMDB`

### Data structure

```python
self.customers: Dict[str, Dict[str, dict]]
# {tenant_id: {customer_id: customer_data}}
```

### Customer record fields

`id`, `name`, `email`, `phone`, `tier`, `notes`, `history`

### Seed data (tenant_a)

| ID | Name | Tier |
|----|------|------|
| `cust_101` | Alice Johnson | gold |
| `cust_102` | Bob Smith | silver |
| `cust_103` | Charlie Brown | platinum |

### Seed data (tenant_b)

| ID | Name | Tier |
|----|------|------|
| `cust_201` | David Miller | bronze |
| `cust_202` | Emily Watson | gold |

---

### `get_customer(tenant_id, customer_id) -> Optional[dict]`

**Returns:** Customer dict or `None` (tenant-isolated)

---

### `update_customer(tenant_id, customer_id, updates: dict) -> dict`

**Returns:** `{"status": "success", "customer": {...}}` or error

Only updates fields in `["name", "email", "phone", "tier"]`.

---

### `add_customer_note(tenant_id, customer_id, note) -> dict`

Appends `"\nUpdate: {note}"` to existing notes field.

---

## Singleton: `crm_db = CRMDB()`

---

## MCP connection

Accessed only by MCP tool handlers in `crm/server.py`. Backend reaches this data exclusively through the MCP protocol.

---

## MCP novice notes

Customer IDs like `cust_101` link to orders (`ord_101` shares the same customer). The agent can chain MCP calls: get order → extract customer_id → get customer profile.
