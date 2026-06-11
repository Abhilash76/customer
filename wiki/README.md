# Customer Support MCP Platform — Wiki

**Start with [Repository Guide](REPOSITORY_GUIDE.md)** for folder-by-folder and file-by-file documentation.

> **Beginner-friendly documentation** for every file in this repository.  
> Start here if you are new to MCP (Model Context Protocol) or LangGraph agents.

---

## Table of Contents

| Section | Description |
|---------|-------------|
| [MCP 101 Primer](#mcp-101-primer) | What MCP is and how this repo uses it |
| [Architecture](#architecture) | System diagram and data flow |
| [How to Run](#how-to-run) | Start the full stack locally |
| [Repo Map](#repo-map) | Links to every wiki page |

---

## MCP 101 Primer

### What is MCP?

**MCP (Model Context Protocol)** is an open standard that lets AI applications connect to external data and tools in a consistent way. Think of it like USB for AI integrations:

- **MCP Server** — Exposes *tools* (actions), *resources* (read-only data), and *prompts* (templates) that an AI can use.
- **MCP Client** — Connects to a server, discovers what's available, and calls tools on behalf of the AI agent.
- **Transport** — How client and server talk. This repo uses **Streamable HTTP** at the `/mcp` endpoint.

### How this repo uses MCP

```mermaid
flowchart LR
    subgraph UI["Frontend (Streamlit)"]
        Chat["Chat UI"]
    end

    subgraph Backend["Backend (FastAPI + LangGraph)"]
        Agent["LangGraph Agent"]
        LLM["OpenAI GPT-4o"]
        Tools["LangChain Tools"]
        Clients["MCP Clients"]
    end

    subgraph MCPServers["MCP Servers (FastMCP)"]
        Orders["Orders MCP :8001/mcp"]
        CRM["CRM MCP :8002/mcp"]
        Tickets["Tickets MCP :8003/mcp"]
    end

    Chat -->|"WebSocket + JWT"| Agent
    Agent --> LLM
    LLM -->|"tool calls"| Tools
    Tools --> Clients
    Clients -->|"streamable_http_client"| Orders
    Clients --> CRM
    Clients --> Tickets
```

1. A support agent types a message in the **Streamlit frontend**.
2. The message travels over **WebSocket** to the **FastAPI backend**, authenticated with a **JWT token**.
3. A **LangGraph agent** (powered by **OpenAI GPT-4o**) decides whether to answer directly or call a tool.
4. Tools are thin wrappers around **MCP clients** that call remote **MCP servers** over HTTP.
5. Each MCP server owns a domain: **orders**, **CRM**, or **tickets**.

### Key MCP concepts in this repo

| Concept | Where it lives | Example |
|---------|----------------|---------|
| **Tool** | MCP server (`@mcp.tool()`) | `search_orders_v1`, `create_ticket` |
| **Resource** | MCP server (`@mcp.resource()`) | `orders://refund-policy` |
| **Prompt** | MCP server (`@mcp.prompt()`) | `executive_summary` |
| **Client session** | `backend/mcp_clients/base.py` | `ClientSession` + `streamable_http_client` |
| **Server transport** | `mcp_servers/*/server.py` | `mcp.run(transport="streamable-http")` |

### Human-in-the-loop (refunds > $1,000)

When the agent tries to refund an order worth more than **$1,000**, LangGraph **pauses** execution and asks a human supervisor to approve or deny. This uses LangGraph's `interrupt()` mechanism — the graph state is saved in PostgreSQL and resumed when the user clicks Approve/Deny in the UI.

### Multi-tenancy & roles

- **Tenants:** `tenant_a` and `tenant_b` — data is isolated per tenant.
- **Roles:** `admin`, `support`, `viewer` — each role can only call certain tools.
- JWT tokens carry `user_id`, `tenant_id`, and `role` claims.

---

## Architecture

```mermaid
flowchart TB
    subgraph DockerCompose["Docker Compose Stack"]
        PG[(PostgreSQL)]
        Redis[(Redis)]
        Prom[Prometheus :9090]

        subgraph MCP["MCP Servers"]
            OM[orders_mcp :8001]
            CM[crm_mcp :8002]
            TM[tickets_mcp :8003]
        end

        BE[backend :8000]
        FE[frontend :8501]
    end

    User((User)) --> FE
    FE -->|"ws://backend:8000/ws/chat"| BE
    BE --> PG
    BE --> Redis
    BE --> OM
    BE --> CM
    BE --> TM
    OM --> Redis
    Prom -->|scrape /metrics| BE
```

### Request lifecycle (chat message)

```mermaid
sequenceDiagram
    participant U as User (Streamlit)
    participant WS as WebSocket API
    participant LG as LangGraph Agent
    participant LLM as OpenAI GPT-4o
    participant MCP as MCP Client
    participant SRV as MCP Server

    U->>WS: user_message + JWT + openai_api_key
    WS->>LG: astream_events(input)
    LG->>LLM: ainvoke(messages + tools)
    LLM-->>LG: AIMessage with tool_calls
    LG->>MCP: call_tool_with_retry()
    MCP->>SRV: HTTP /mcp (streamable)
    SRV-->>MCP: JSON result
    MCP-->>LG: ToolMessage
    LG->>LLM: ainvoke(updated messages)
    LLM-->>LG: final answer
    LG-->>WS: stream tokens + tool events
    WS-->>U: final response
```

---

## How to Run

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- An **OpenAI API key** (enter in Streamlit sidebar or set in `.env`)

### Quick start

```bash
# 1. Clone and enter the repo
cd customer

# 2. Copy environment template (optional — key can be entered in UI)
cp .env.example .env
# Edit .env and set OPENAI_API_KEY=sk-...

# 3. Start all services
docker compose up --build

# 4. Open the chat UI
# http://localhost:8501
```

### Services & ports

| Service | Port | URL / Endpoint |
|---------|------|----------------|
| Frontend (Streamlit) | 8501 | http://localhost:8501 |
| Backend (FastAPI) | 8000 | http://localhost:8000/health |
| Orders MCP | 8001 | http://localhost:8001/mcp |
| CRM MCP | 8002 | http://localhost:8002/mcp |
| Tickets MCP | 8003 | http://localhost:8003/mcp |
| PostgreSQL | 5432 | `postgresql://user:password@localhost:5432/support` |
| Redis | 6379 | `redis://localhost:6379/0` |
| Prometheus | 9090 | http://localhost:9090 |

### Demo workflow

1. Open http://localhost:8501
2. Enter your **OpenAI API key** in the sidebar
3. Select a demo user (e.g. **Alice Admin, Tenant A**)
4. Click **Log In / Change Role**
5. Try prompts like:
   - *"Show me all orders for tenant_a"*
   - *"Get details for order ord_102"* (amount $1,200 — triggers approval)
   - *"Create a ticket for customer cust_101 about a late delivery"*

### Running tests

```bash
# From repo root (with backend on PYTHONPATH via conftest)
pytest tests/ -v
```

---

## Repo Map

### Root & infrastructure

| Source file | Wiki page |
|-------------|-----------|
| `docker-compose.yml` | [docker-compose.yml.md](docker-compose.yml.md) |
| `.env.example` | [.env.example.md](.env.example.md) |
| `db/init.sql` | [db/init.sql.md](db/init.sql.md) |
| `monitoring/prometheus.yml` | [monitoring/prometheus.yml.md](monitoring/prometheus.yml.md) |

### Backend

| Source file | Wiki page |
|-------------|-----------|
| `backend/main.py` | [backend/main.py.md](backend/main.py.md) |
| `backend/config.py` | [backend/config.py.md](backend/config.py.md) |
| `backend/logging_config.py` | [backend/logging_config.py.md](backend/logging_config.py.md) |
| `backend/requirements.txt` | [backend/requirements.txt.md](backend/requirements.txt.md) |
| `backend/Dockerfile` | [backend/Dockerfile.md](backend/Dockerfile.md) |
| `backend/api/health.py` | [backend/api/health.py.md](backend/api/health.py.md) |
| `backend/api/metrics.py` | [backend/api/metrics.py.md](backend/api/metrics.py.md) |
| `backend/api/approval.py` | [backend/api/approval.py.md](backend/api/approval.py.md) |
| `backend/api/websocket.py` | [backend/api/websocket.py.md](backend/api/websocket.py.md) |
| `backend/auth/jwt_handler.py` | [backend/auth/jwt_handler.py.md](backend/auth/jwt_handler.py.md) |
| `backend/auth/permissions.py` | [backend/auth/permissions.py.md](backend/auth/permissions.py.md) |
| `backend/db/postgres.py` | [backend/db/postgres.py.md](backend/db/postgres.py.md) |
| `backend/db/redis.py` | [backend/db/redis.py.md](backend/db/redis.py.md) |
| `backend/mcp_clients/base.py` | [backend/mcp_clients/base.py.md](backend/mcp_clients/base.py.md) |
| `backend/mcp_clients/orders.py` | [backend/mcp_clients/orders.py.md](backend/mcp_clients/orders.py.md) |
| `backend/mcp_clients/crm.py` | [backend/mcp_clients/crm.py.md](backend/mcp_clients/crm.py.md) |
| `backend/mcp_clients/tickets.py` | [backend/mcp_clients/tickets.py.md](backend/mcp_clients/tickets.py.md) |
| `backend/graph/state.py` | [backend/graph/state.py.md](backend/graph/state.py.md) |
| `backend/graph/tools.py` | [backend/graph/tools.py.md](backend/graph/tools.py.md) |
| `backend/graph/nodes.py` | [backend/graph/nodes.py.md](backend/graph/nodes.py.md) |
| `backend/graph/builder.py` | [backend/graph/builder.py.md](backend/graph/builder.py.md) |

### MCP Servers

| Source file | Wiki page |
|-------------|-----------|
| `mcp_servers/orders/server.py` | [mcp_servers/orders/server.py.md](mcp_servers/orders/server.py.md) |
| `mcp_servers/orders/auth.py` | [mcp_servers/orders/auth.py.md](mcp_servers/orders/auth.py.md) |
| `mcp_servers/orders/db.py` | [mcp_servers/orders/db.py.md](mcp_servers/orders/db.py.md) |
| `mcp_servers/crm/server.py` | [mcp_servers/crm/server.py.md](mcp_servers/crm/server.py.md) |
| `mcp_servers/crm/db.py` | [mcp_servers/crm/db.py.md](mcp_servers/crm/db.py.md) |
| `mcp_servers/tickets/server.py` | [mcp_servers/tickets/server.py.md](mcp_servers/tickets/server.py.md) |
| `mcp_servers/tickets/db.py` | [mcp_servers/tickets/db.py.md](mcp_servers/tickets/db.py.md) |

### Frontend

| Source file | Wiki page |
|-------------|-----------|
| `frontend/app.py` | [frontend/app.py.md](frontend/app.py.md) |
| `frontend/ws_client.py` | [frontend/ws_client.py.md](frontend/ws_client.py.md) |

### Tests

| Source file | Wiki page |
|-------------|-----------|
| `tests/conftest.py` | [tests/conftest.py.md](tests/conftest.py.md) |
| `tests/test_auth.py` | [tests/test_auth.py.md](tests/test_auth.py.md) |
| `tests/test_mcp_servers.py` | [tests/test_mcp_servers.py.md](tests/test_mcp_servers.py.md) |
| `tests/test_tools.py` | [tests/test_tools.py.md](tests/test_tools.py.md) |

---

## Glossary

| Term | Meaning |
|------|---------|
| **FastMCP** | Python helper library to build MCP servers quickly |
| **Streamable HTTP** | MCP transport over HTTP; endpoint is `/mcp` |
| **LangGraph** | Framework for building stateful AI agent workflows as graphs |
| **Checkpointer** | Saves graph state to DB so conversations can resume |
| **Tool** | A callable function the LLM can invoke (e.g. search orders) |
| **Interrupt** | Pauses graph execution until human input arrives |
| **Tenant** | An isolated customer organization (`tenant_a`, `tenant_b`) |
