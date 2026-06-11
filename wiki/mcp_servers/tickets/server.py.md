# mcp_servers/tickets/server.py

> **Source:** `mcp_servers/tickets/server.py`  
> **Purpose:** Tickets MCP server — support ticket CRUD via FastMCP.

---

## Imports

| Import | Library | Why used |
|--------|---------|----------|
| `os, json, logging` | stdlib | Config, serialization, logging |
| `Optional, List` | `typing` | Type hints |
| `FastMCP` | `mcp.server.fastmcp` | MCP server framework |
| `tickets_db` | `db` | Mock tickets database |

---

## Server initialization

```python
mcp = FastMCP("tickets_mcp", host="0.0.0.0", port=int(os.getenv("PORT", 8003)))
```

Endpoint: `http://tickets_mcp:8003/mcp` (Streamable HTTP)

---

## MCP Tools

### `create_ticket(tenant_id, customer_id, subject, priority="medium") -> str`

Creates a new ticket with auto-generated ID (`tkt_XXXX`).

### `search_ticket(tenant_id, customer_id=None) -> str`

Returns JSON list of tickets, optionally filtered by customer.

### `update_ticket(tenant_id, ticket_id, status=None, priority=None) -> str`

Updates ticket status (`open`, `in_progress`, `closed`) and/or priority.

---

## MCP Resources

### `tickets://templates`

Returns JSON templates for common ticket types:
- `refund_request`
- `shipping_delay`
- `technical_support`

---

## MCP connection

```mermaid
flowchart LR
    TMC["tickets_mcp_client"] -->|"http://tickets_mcp:8003/mcp"| SRV["tickets_mcp"]
    SRV --> DB["tickets_db"]
```

---

## MCP novice notes

Tickets MCP is the simplest server — 3 tools, 1 resource, no auth, no caching. Good starting point for understanding MCP server anatomy before exploring orders (auth + cache) or CRM (resources).
