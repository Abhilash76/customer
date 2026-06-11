# backend/config.py

> **Source:** `backend/config.py`  
> **Purpose:** Centralized configuration loaded from environment variables and `.env` file.

---

## Imports

| Import | Library | Why used |
|--------|---------|----------|
| `os` | stdlib | Read environment variables |
| `BaseSettings` | `pydantic-settings` | Typed settings with `.env` support |

---

## Class: `Settings(BaseSettings)`

A Pydantic model that loads all configuration at import time.

| Field | Default | Env var | Description |
|-------|---------|---------|-------------|
| `OPENAI_API_KEY` | `""` | `OPENAI_API_KEY` | OpenAI API key (fallback if not sent via WebSocket) |
| `JWT_SECRET` | `"your-secret-key"` | `JWT_SECRET` | HMAC secret for JWT signing |
| `JWT_ALGORITHM` | `"HS256"` | — | JWT algorithm (fixed) |
| `POSTGRES_URL` | `postgresql+asyncpg://user:password@postgres:5432/support` | `POSTGRES_URL` | Async PostgreSQL DSN |
| `REDIS_URL` | `redis://redis:6379/0` | `REDIS_URL` | Redis connection string |
| `ORDERS_MCP_URL` | `http://orders_mcp:8001/mcp` | `ORDERS_MCP_URL` | Orders MCP Streamable HTTP endpoint |
| `CRM_MCP_URL` | `http://crm_mcp:8002/mcp` | `CRM_MCP_URL` | CRM MCP endpoint |
| `TICKETS_MCP_URL` | `http://tickets_mcp:8003/mcp` | `TICKETS_MCP_URL` | Tickets MCP endpoint |
| `LANGCHAIN_TRACING_V2` | `false` | `LANGCHAIN_TRACING_V2` | Enable LangSmith tracing |
| `LANGCHAIN_API_KEY` | `""` | `LANGCHAIN_API_KEY` | LangSmith API key |
| `LANGCHAIN_PROJECT` | `"customer-support"` | `LANGCHAIN_PROJECT` | LangSmith project name |

**Nested `Config` class:**
- `env_file = ".env"` — loads from `.env` if present
- `extra = "ignore"` — ignores unknown env vars

---

## Singleton: `settings`

```python
settings = Settings()
```

Imported throughout the backend as `from config import settings`.

---

## MCP connection

The three `*_MCP_URL` fields are the **addresses** MCP clients connect to. The `/mcp` suffix is the Streamable HTTP transport path required by the `mcp` Python package's `streamable_http_client`.

```mermaid
flowchart LR
    CFG["config.settings"] --> OC["ORDERS_MCP_URL"]
    CFG --> CC["CRM_MCP_URL"]
    CFG --> TC["TICKETS_MCP_URL"]
    OC --> OMC["orders_mcp_client"]
    CC --> CMC["crm_mcp_client"]
    TC --> TMC["tickets_mcp_client"]
```

---

## MCP novice notes

MCP server URLs are configuration, not code. Changing a port in `docker-compose.yml` requires updating the matching `*_MCP_URL` here (or in the compose environment block).
