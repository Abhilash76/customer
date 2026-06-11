# backend/mcp_clients/tickets.py

> **Source:** `backend/mcp_clients/tickets.py`  
> **Purpose:** MCP client for the Tickets server — create, search, and update support tickets.

---

## Imports

| Import | Library | Why used |
|--------|---------|----------|
| `json` | stdlib | Parse MCP JSON responses |
| `logging` | stdlib | Logging |
| `Dict, Any, Optional` | `typing` | Type hints |
| `BaseMCPClient` | `mcp_clients.base` | MCP connection base |
| `settings` | `config` | `TICKETS_MCP_URL` |

---

## Class: `TicketsMCPClient(BaseMCPClient)`

### `__init__(self)`

`super().__init__(settings.TICKETS_MCP_URL, "tickets_mcp")`

---

### `create_ticket(tenant_id, customer_id, subject, priority="medium") -> Dict`

Calls MCP tool `create_ticket`. Returns new ticket dict with generated ID.

---

### `search_ticket(tenant_id, customer_id=None) -> Dict`

Calls `search_ticket` — optional filter by customer.

---

### `update_ticket(tenant_id, ticket_id, status=None, priority=None) -> Dict`

Calls `update_ticket` with optional status/priority changes.

**Note:** No Redis caching — ticket data changes frequently.

---

## Singleton: `tickets_mcp_client = TicketsMCPClient()`

---

## MCP tools mapped

| Client method | MCP tool |
|---------------|----------|
| `create_ticket` | `create_ticket` |
| `search_ticket` | `search_ticket` |
| `update_ticket` | `update_ticket` |

---

## MCP connection

```mermaid
flowchart LR
    TOOLS["graph/tools.py"] --> TMC["tickets_mcp_client"]
    TMC -->|"http://tickets_mcp:8003/mcp"| SRV["tickets_mcp server"]
```

The Tickets MCP server also exposes a **resource** `tickets://templates` with pre-built ticket templates — not used by this client but available to MCP-aware tools.

---

## MCP novice notes

Tickets are the simplest client — no caching, no JWT. The pattern is: thin wrapper → `call_tool_with_retry` → parse JSON. This is the minimal MCP client integration.
