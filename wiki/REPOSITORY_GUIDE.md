# Repository Guide

> **Audience:** MCP novices. This document walks through every folder and file in the Customer Support MCP platform so you can understand what each piece does and how they connect.

---

## Table of Contents

- [Project Root](#project-root)
- [db/](#db)
- [backend/](#backend)
- [backend/api/](#backendapi)
- [backend/auth/](#backendauth)
- [backend/db/](#backenddb)
- [backend/mcp_clients/](#backendmcp_clients)
- [backend/graph/](#backendgraph)
- [mcp_servers/](#mcp_servers)
- [mcp_servers/orders/](#mcp_serversorders)
- [mcp_servers/crm/](#mcp_serverscrm)
- [mcp_servers/tickets/](#mcp_serverstickets)
- [frontend/](#frontend)
- [tests/](#tests)
- [monitoring/](#monitoring)

---

## Project Root

### Folder Summary: Project Root

The project root is the entry point for running the entire platform. It contains `docker-compose.yml`, which orchestrates every service—PostgreSQL, Redis, three MCP servers, the FastAPI backend, the Streamlit frontend, and Prometheus—into a single `docker compose up` command. The `.env.example` file documents the environment variables you can set before starting the stack, though the OpenAI API key can also be entered directly in the Streamlit sidebar at runtime. When you run Docker Compose, PostgreSQL automatically loads the schema from `db/init.sql` on first boot. The backend connects to all three MCP servers over **Streamable HTTP** at their `/mcp` endpoints. The frontend talks to the backend over a WebSocket at `/ws/chat`, passing a JWT token for authentication and an `openai_api_key` field in each chat message. This root-level layout keeps infrastructure configuration separate from application code, which lives in `backend/`, `mcp_servers/`, and `frontend/`.

### docker-compose.yml

**What it does:** Defines the full Docker Compose stack with eight services. It wires PostgreSQL (with `db/init.sql` mounted as an init script), Redis, three MCP servers (orders on port 8001, CRM on 8002, tickets on 8003), the FastAPI backend on 8000, the Streamlit frontend on 8501, and Prometheus on 9090. Health checks ensure Postgres and Redis are ready before dependent services start. Environment variables pass JWT secrets, database URLs, and MCP server URLs between containers.

**Imports / references:**

| Name | Why we need it |
|------|----------------|
| `postgres` service | Persistent database for conversations, messages, approvals, and LangGraph checkpoints |
| `redis` service | Shared cache used by the backend and Orders MCP server |
| `orders_mcp` service | Orders domain MCP server with JWT auth at `http://orders_mcp:8001/mcp` |
| `crm_mcp` service | CRM domain MCP server (no JWT) at `http://crm_mcp:8002/mcp` |
| `tickets_mcp` service | Tickets domain MCP server (no JWT) at `http://tickets_mcp:8003/mcp` |
| `backend` service | FastAPI + LangGraph agent; depends on all data stores and MCP servers |
| `frontend` service | Streamlit chat UI; connects to backend WebSocket |
| `prometheus` service | Scrapes backend `/metrics` using `monitoring/prometheus.yml` |
| `pgdata`, `redisdata` volumes | Persist database data across container restarts |

**Key configuration blocks:**

| Block | What it does |
|-------|--------------|
| `postgres` | Runs Postgres 16, mounts `db/init.sql`, exposes port 5432 |
| `orders_mcp` | Builds from `mcp_servers/orders`, sets `JWT_SECRET` and `REDIS_URL` |
| `backend` | Sets `ORDERS_MCP_URL`, `CRM_MCP_URL`, `TICKETS_MCP_URL` pointing to `/mcp` endpoints |
| `frontend` | Sets `BACKEND_URL=ws://backend:8000/ws/chat` and `JWT_SECRET` |

### .env.example

**What it does:** Template for optional environment variables used when running the stack outside Docker or when you want server-side defaults. Documents `OPENAI_API_KEY` (optional if entered in the Streamlit sidebar), LangChain tracing settings, and `JWT_SECRET`. Copy this to `.env` before `docker compose up` if you prefer not to type the API key in the UI.

**Variables:**

| Variable | What it does |
|----------|--------------|
| `OPENAI_API_KEY` | Default OpenAI key for the backend (overridden per-session by the Streamlit sidebar) |
| `LANGCHAIN_TRACING_V2` | Enables LangSmith tracing when set to `true` |
| `LANGCHAIN_API_KEY` | LangSmith API key for tracing |
| `LANGCHAIN_PROJECT` | Project name in LangSmith (default: `customer-support`) |
| `JWT_SECRET` | Shared secret for signing JWT tokens across backend, frontend, and Orders MCP |

---

## db/

### Folder Summary: db/

The `db/` folder holds database initialization scripts that run automatically when PostgreSQL starts for the first time. Docker Compose mounts `init.sql` into the Postgres container's `docker-entrypoint-initdb.d/` directory, so the schema and seed data are created before any application code connects. The schema defines tables for users, conversations, messages, tool executions, and approvals—all supporting multi-tenant isolation with indexes on `tenant_id` and `thread_id`. Seed users cover both tenants (`tenant_a` and `tenant_b`) and all three roles (`admin`, `support`, `viewer`), matching the demo users in the Streamlit sidebar. LangGraph also uses this same PostgreSQL instance for checkpointing conversation state via `AsyncPostgresSaver`. The MCP servers themselves use in-memory mock databases (`db.py` in each server folder), not this PostgreSQL schema—the Postgres database is owned by the backend for chat history, audit logs, and human-in-the-loop approval records.

### init.sql

**What it does:** Creates the PostgreSQL schema for the backend platform. Defines five tables (`users`, `conversations`, `messages`, `tool_executions`, `approvals`) with foreign keys and tenant-scoped indexes. Seeds five demo users across `tenant_a` and `tenant_b` with roles `admin`, `support`, and `viewer`. The `approvals` table tracks pending refund decisions for the LangGraph human-in-the-loop flow.

**SQL objects:**

| Object | What it does |
|--------|--------------|
| `users` table | Stores user profiles with `tenant_id` and `role` for JWT-based auth |
| `conversations` table | Maps LangGraph `thread_id` values to conversation records per tenant |
| `messages` table | Persists chat messages (user and assistant) with optional JSON metadata |
| `tool_executions` table | Audit log of every tool call with input, output, latency, and status |
| `approvals` table | Records refund approval requests with amount, status, and reviewer |
| `idx_*` indexes | Speed up tenant-scoped queries and thread lookups |
| `INSERT INTO users` | Seeds Alice, Bob, Charlie (tenant_a) and Dave, Eve (tenant_b) |

---

## backend/

### Folder Summary: backend/

The `backend/` folder is the brain of the platform—a FastAPI application that hosts the LangGraph AI agent, WebSocket chat API, and all supporting infrastructure. `main.py` is the entry point: on startup it connects to PostgreSQL and Redis, initializes three MCP clients (orders, CRM, tickets) over **Streamable HTTP**, and compiles the LangGraph workflow with a Postgres checkpointer. `config.py` centralizes all environment variables (API keys, database URLs, MCP server URLs). `logging_config.py` sets up structured JSON logging for observability. The `api/` subfolder exposes HTTP and WebSocket endpoints; `auth/` handles JWT creation and role-based permissions; `db/` wraps PostgreSQL and Redis; `mcp_clients/` connects to remote MCP servers; and `graph/` defines the LangGraph agent (state, tools, nodes, builder). When a user sends a chat message, the WebSocket handler streams LangGraph events back token-by-token. Refunds over $1,000 trigger a human-in-the-loop pause stored in PostgreSQL until a supervisor approves or denies via the UI.

### main.py

**What it does:** FastAPI application entry point. Manages the application lifespan (connect/disconnect databases, MCP clients, and LangGraph). Registers routers for health, metrics, approval, and WebSocket chat. Exposes a demo `/api/token` endpoint so the Streamlit frontend can obtain JWT tokens for test users.

**Imports:**

| Import | Why we need it |
|--------|----------------|
| `fastapi.FastAPI` | Web framework for HTTP and WebSocket APIs |
| `fastapi.middleware.cors.CORSMiddleware` | Allows cross-origin requests from the Streamlit frontend |
| `contextlib.asynccontextmanager` | Defines startup/shutdown lifecycle hooks |
| `config.settings` | Reads environment variables |
| `logging_config.setup_logging` | Configures JSON structured logging |
| `db.postgres.postgres_db` | PostgreSQL connection pool manager |
| `db.redis.redis_cache` | Redis cache manager |
| `mcp_clients.orders/crm/tickets` | MCP client singletons for each domain server |
| `graph.builder.graph_builder` | LangGraph workflow compiler |
| `auth.jwt_handler.create_access_token` | Generates demo JWT tokens |
| `api.health/metrics/approval/websocket` | API route modules |

**Methods / endpoints:**

| Name | What it does |
|------|--------------|
| `lifespan(app)` | Async context manager: connects DBs, MCP clients, and LangGraph on startup; disconnects on shutdown |
| `generate_token_for_demo(req)` | `POST /api/token` — creates a JWT for a given user_id, tenant_id, and role |
| `app` (FastAPI instance) | Main application with CORS middleware and four included routers |

### config.py

**What it does:** Defines a `Settings` class using `pydantic-settings` to load configuration from environment variables and `.env` file. Centralizes all URLs, secrets, and feature flags so every backend module reads from a single `settings` singleton.

**Imports:**

| Import | Why we need it |
|--------|----------------|
| `os` | Reads environment variables as defaults |
| `pydantic_settings.BaseSettings` | Typed settings with automatic env loading |

**Classes / objects:**

| Name | What it does |
|------|--------------|
| `Settings` | Dataclass-like config with `OPENAI_API_KEY`, `JWT_SECRET`, `POSTGRES_URL`, `REDIS_URL`, MCP URLs, and LangChain tracing fields |
| `settings` | Singleton instance used across the backend |

### logging_config.py

**What it does:** Configures structured JSON logging for the entire backend. Every log line includes timestamp, level, message, logger name, and optional context fields (`tenant_id`, `user_id`, `thread_id`, `tool_name`, `latency`, `status`). This makes logs easy to search in production observability tools.

**Imports:**

| Import | Why we need it |
|--------|----------------|
| `logging` | Python standard logging module |
| `json` | Serializes log records to JSON strings |
| `datetime` | Formats timestamps in ISO 8601 |
| `typing.Any, Dict` | Type hints for log data dictionary |

**Classes / functions:**

| Name | What it does |
|------|--------------|
| `JSONFormatter` | Custom `logging.Formatter` that outputs one JSON object per log line |
| `JSONFormatter.format(record)` | Builds the JSON dict from a log record, including custom fields |
| `setup_logging()` | Configures root logger with INFO level and JSON stream handler |
| `get_logger(name)` | Returns a named logger instance |

### requirements.txt

**What it does:** Lists all Python dependencies for the backend Docker image. Includes FastAPI, LangGraph (with Postgres checkpointer), LangChain OpenAI integration, MCP client libraries, asyncpg, Redis, JWT, OpenTelemetry, Prometheus, and test tools.

**Key packages:**

| Package | Why we need it |
|---------|----------------|
| `fastapi`, `uvicorn` | Web server framework and ASGI runtime |
| `langgraph`, `langgraph-checkpoint-postgres` | Stateful AI agent workflow with DB persistence |
| `langchain-core`, `langchain-openai` | LLM integration with GPT-4o |
| `mcp`, `langchain-mcp-adapters` | MCP client protocol support |
| `asyncpg` | Async PostgreSQL driver |
| `redis[hiredis]` | Async Redis client |
| `python-jose[cryptography]` | JWT encoding and decoding |
| `prometheus-client` | Exposes `/metrics` endpoint |
| `pytest`, `pytest-asyncio`, `httpx` | Testing dependencies |

### Dockerfile

**What it does:** Builds the backend Docker image. Uses Python 3.11 slim, installs dependencies from `requirements.txt`, copies application code, exposes port 8000, and runs `python main.py` to start Uvicorn.

**Stages / commands:**

| Step | What it does |
|------|--------------|
| `FROM python:3.11-slim` | Base image with Python 3.11 |
| `COPY requirements.txt` + `pip install` | Installs all backend dependencies |
| `COPY . .` | Copies backend source code into `/app` |
| `EXPOSE 8000` | Documents the API port |
| `CMD ["python", "main.py"]` | Starts the FastAPI server |

---

## backend/api/

### Folder Summary

The `backend/api/` folder contains all HTTP and WebSocket route handlers exposed by the FastAPI application. Each file defines an `APIRouter` that `main.py` includes at startup. `health.py` provides a `/health` endpoint that checks PostgreSQL and Redis connectivity—useful for Docker health checks and load balancers. `metrics.py` exposes a `/metrics` endpoint in Prometheus format, tracking tool call counts, failures, latency histograms, and active WebSocket sessions. `approval.py` handles the REST-based human-in-the-loop flow: when a supervisor approves or denies a refund, it updates the `approvals` table and resumes the paused LangGraph thread with a `Command(resume=...)`. `websocket.py` is the primary chat interface: it authenticates via JWT query parameter, receives `user_message` and `approval_response` events, runs the LangGraph agent, and streams back thinking indicators, tokens, tool events, and approval prompts in real time. The WebSocket also accepts `openai_api_key` in each message so users can supply their key from the Streamlit sidebar.

### health.py

**What it does:** Exposes `GET /health` to verify backend readiness. Pings PostgreSQL (`SELECT 1`) and Redis (`PING`) and returns an overall status of `healthy` or `degraded` with per-dependency details.

**Imports:**

| Import | Why we need it |
|--------|----------------|
| `fastapi.APIRouter` | Defines a modular route group |
| `db.postgres.postgres_db` | Checks Postgres pool connectivity |
| `db.redis.redis_cache` | Checks Redis client connectivity |

**Functions:**

| Name | What it does |
|------|--------------|
| `health_check()` | `GET /health` — returns status, version, and postgres/redis health |

### metrics.py

**What it does:** Exposes `GET /metrics` in Prometheus exposition format. Defines counters for tool calls and failures, a histogram for tool latency, and a gauge for active WebSocket sessions. Scraped by the Prometheus container defined in `docker-compose.yml`.

**Imports:**

| Import | Why we need it |
|--------|----------------|
| `fastapi.APIRouter, Response` | Route handler and raw response type |
| `prometheus_client.Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST` | Prometheus metric types and output formatter |

**Objects / functions:**

| Name | What it does |
|------|--------------|
| `TOOL_CALLS_TOTAL` | Counter labeled by tool_name, tenant_id, status |
| `TOOL_FAILURES_TOTAL` | Counter labeled by tool_name, error_type |
| `TOOL_LATENCY_SECONDS` | Histogram of tool execution duration |
| `ACTIVE_SESSIONS` | Gauge of current WebSocket connections |
| `get_metrics()` | `GET /metrics` — returns Prometheus text format |

### approval.py

**What it does:** Handles `POST /api/human-approval` for resuming LangGraph threads paused by refund approval interrupts. Updates the `approvals` table in PostgreSQL, then invokes `graph.ainvoke(Command(resume=...))` to continue execution after a supervisor decision.

**Imports:**

| Import | Why we need it |
|--------|----------------|
| `fastapi.APIRouter, HTTPException` | Route handler and error responses |
| `pydantic.BaseModel` | Request body validation |
| `langgraph.types.Command` | LangGraph resume command for interrupted threads |
| `db.postgres.postgres_db` | Updates approval status in database |
| `graph.builder.graph_builder` | Access to compiled LangGraph instance |

**Classes / functions:**

| Name | What it does |
|------|--------------|
| `ApprovalPayload` | Pydantic model with `thread_id`, `approved`, `reviewer_id` |
| `resolve_approval(payload)` | `POST /api/human-approval` — updates DB and resumes graph |

### websocket.py

**What it does:** Primary chat interface at `WS /ws/chat`. Authenticates connections via JWT in query params. Handles `user_message` (runs LangGraph and streams events), `approval_response` (resumes paused threads), and `ping`/`pong` keepalives. Streams thinking indicators, LLM tokens, tool start/result events, human approval prompts, and final answers. Accepts `openai_api_key` in each message payload from the Streamlit sidebar.

**Imports:**

| Import | Why we need it |
|--------|----------------|
| `fastapi.APIRouter, WebSocket, WebSocketDisconnect` | WebSocket route handling |
| `starlette.websockets.WebSocketState` | Checks if connection is still open during streaming |
| `langchain_core.messages.HumanMessage` | Formats user input for LangGraph |
| `langgraph.types.Command` | Resumes interrupted graph threads |
| `auth.jwt_handler.decode_token` | Validates JWT from query parameter |
| `graph.builder.graph_builder` | Runs and streams LangGraph events |
| `db.postgres.postgres_db` | Saves messages and records approval requests |
| `api.metrics.*` | Increments Prometheus counters during tool execution |

**Functions:**

| Name | What it does |
|------|--------------|
| `run_graph_and_stream(...)` | Runs LangGraph with `astream_events`, sends JSON events over WebSocket; checks for approval interrupts after streaming |
| `websocket_chat_endpoint(websocket)` | `WS /ws/chat` — accepts connection, loops on incoming messages, dispatches to `run_graph_and_stream` |

---

## backend/auth/

### Folder Summary

The `backend/auth/` folder implements authentication and authorization for the platform. `jwt_handler.py` creates and validates JWT tokens carrying `user_id`, `tenant_id`, and `role` claims—used by the WebSocket chat endpoint, the demo token API, and passed through to the Orders MCP server for server-side permission checks. `permissions.py` defines the role-to-tool mapping that controls which MCP tools each user can invoke. Three roles exist: `admin` (full access to all 10 tools), `support` (read orders, read customers, create/search tickets—no refunds), and `viewer` (read-only across orders, customers, and tickets). Two tenants (`tenant_a` and `tenant_b`) isolate data at every layer. The LangGraph `tool_node` injects `tenant_id` and `token` from state into tool arguments, and `get_tools_for_role()` filters the tool list before binding to the LLM—so the AI never even sees tools the user cannot call.

### jwt_handler.py

**What it does:** Creates, decodes, and validates JWT access tokens using HS256 and the shared `JWT_SECRET`. Tokens carry `user_id`, `tenant_id`, `role`, and `exp` (24-hour default expiry). Also provides a WebSocket authentication helper that reads the token from query params or Authorization header.

**Imports:**

| Import | Why we need it |
|--------|----------------|
| `datetime.datetime, timedelta` | Sets token expiration timestamps |
| `jose.jwt, JWTError` | JWT encoding and decoding |
| `fastapi.WebSocket, WebSocketException, status` | WebSocket auth helper |
| `config.settings` | Reads `JWT_SECRET` and `JWT_ALGORITHM` |

**Functions:**

| Name | What it does |
|------|--------------|
| `create_access_token(user_id, tenant_id, role, expires_delta)` | Signs a JWT with user claims and expiration |
| `decode_token(token)` | Validates and decodes a JWT; returns claims dict or `None` |
| `authenticate_websocket(websocket)` | Extracts token from query/header, validates, returns claims or closes connection |

### permissions.py

**What it does:** Defines the `ROLE_PERMISSIONS` mapping and helper functions to check whether a role can call a specific MCP tool. Used by the LangGraph tool node and `get_tools_for_role()` to filter available tools before the LLM sees them.

**Imports:**

| Import | Why we need it |
|--------|----------------|
| `typing.Set, Dict, List` | Type hints for permission data structures |

**Constants / functions:**

| Name | What it does |
|------|--------------|
| `ROLE_PERMISSIONS` | Dict mapping `admin`, `support`, `viewer` to sets of allowed tool names |
| `has_permission(role, tool_name)` | Returns `True` if the role may call the tool |
| `filter_permitted_tools(role, tools)` | Filters a list of MCP tool dicts to only those allowed for the role |

---

## backend/db/

### Folder Summary

The `backend/db/` folder provides async database access for PostgreSQL and Redis. `postgres.py` manages an `asyncpg` connection pool and exposes tenant-safe methods for conversations, messages, tool execution audit logs, and approval records. It normalizes the SQLAlchemy-style `postgresql+asyncpg://` connection string to `postgresql://` because asyncpg expects the standard scheme. `redis.py` wraps an async Redis client for JSON-serialized caching with TTL support. The backend MCP clients use Redis to cache order and customer lookups (5-minute TTL), invalidating cache entries on writes. PostgreSQL serves three purposes: persisting chat history, logging every tool execution for audit, and storing approval requests for the human-in-the-loop refund flow. LangGraph's `AsyncPostgresSaver` also uses the same database (via a separate connection) to checkpoint graph state so interrupted conversations can resume.

### postgres.py

**What it does:** Async PostgreSQL manager using `asyncpg` connection pooling. Provides generic query methods and tenant-scoped operations for conversations, messages, tool executions, and approvals. Normalizes `postgresql+asyncpg://` URLs to `postgresql://` for asyncpg compatibility.

**Imports:**

| Import | Why we need it |
|--------|----------------|
| `asyncpg` | Async PostgreSQL driver and connection pool |
| `json` | Serializes message metadata to JSONB |
| `config.settings` | Reads `POSTGRES_URL` |
| `logging` | Logs connection events and errors |

**Class `PostgresManager` methods:**

| Name | What it does |
|------|--------------|
| `connect()` | Creates asyncpg pool (normalizes DSN, min 2 / max 10 connections) |
| `close()` | Closes the connection pool |
| `execute(query, *args)` | Runs INSERT/UPDATE/DELETE without returning rows |
| `fetch(query, *args)` | Returns multiple rows |
| `fetchrow(query, *args)` | Returns a single row or `None` |
| `fetchval(query, *args)` | Returns a single scalar value |
| `get_messages(conversation_id, tenant_id)` | Fetches all messages for a tenant-scoped conversation |
| `save_message(conversation_id, tenant_id, role, content, metadata)` | Inserts a message with tenant validation |
| `get_or_create_conversation(thread_id, user_id, tenant_id)` | Finds or creates a conversation for a LangGraph thread |
| `log_tool_execution(conversation_id, tool_name, input_val, output_val, latency_ms, status)` | Audit log entry for a tool call |
| `record_approval_request(thread_id, tool_name, amount)` | Inserts a pending approval record |
| `update_approval_status(thread_id, approved, reviewer_id)` | Marks approval as approved/denied with reviewer and timestamp |
| `postgres_db` | Module-level singleton instance |

### redis.py

**What it does:** Async Redis manager for JSON-serialized caching. Provides get/set/delete operations with configurable TTL (default 300 seconds). Used by MCP clients to cache order and customer lookups.

**Imports:**

| Import | Why we need it |
|--------|----------------|
| `redis.asyncio` (as `aioredis`) | Async Redis client |
| `json` | Serializes/deserializes cached values |
| `config.settings` | Reads `REDIS_URL` |

**Class `RedisManager` methods:**

| Name | What it does |
|------|--------------|
| `connect()` | Creates Redis client from URL and pings to verify |
| `close()` | Closes the Redis connection |
| `get_cache(key)` | Retrieves and JSON-deserializes a cached value |
| `set_cache(key, value, ttl)` | JSON-serializes and stores a value with TTL |
| `delete_cache(key)` | Removes a key from cache |
| `redis_cache` | Module-level singleton instance |

---

## backend/mcp_clients/

### Folder Summary

The `backend/mcp_clients/` folder contains MCP client wrappers that connect the LangGraph agent to the three remote MCP servers. `base.py` defines `BaseMCPClient`, which uses the official MCP Python SDK's `streamable_http_client` to connect to each server's `/mcp` endpoint and wraps `ClientSession` for tool listing and invocation with retry logic. `orders.py`, `crm.py`, and `tickets.py` extend the base client with domain-specific methods that call named MCP tools, parse JSON responses, and manage Redis caching (orders and CRM). The Orders client passes the user's JWT `token` to the server, which validates it server-side. CRM and Tickets clients only pass `tenant_id`—those servers do not require JWT authentication. These clients are initialized at backend startup in `main.py` and used by the LangGraph tool wrappers in `graph/tools.py` to bridge the AI agent and the MCP servers.

### base.py

**What it does:** Abstract base class for all MCP clients. Connects to MCP servers over **Streamable HTTP** using `streamable_http_client` and `ClientSession`. Provides `list_tools()` and `call_tool_with_retry()` with exponential backoff for transient failures. Does not retry permission-denied errors.

**Imports:**

| Import | Why we need it |
|--------|----------------|
| `mcp.ClientSession` | MCP protocol session for tool calls |
| `mcp.client.streamable_http.streamable_http_client` | HTTP transport connecting to `/mcp` endpoint |
| `contextlib.AsyncExitStack` | Manages async context lifecycle for connection |
| `asyncio` | Sleep between retry attempts |

**Class `BaseMCPClient` methods:**

| Name | What it does |
|------|--------------|
| `__init__(server_url, server_name)` | Stores server URL and name |
| `connect()` | Opens Streamable HTTP connection and initializes MCP session |
| `close()` | Tears down connection via exit stack |
| `list_tools()` | Calls `session.list_tools()` and returns tool dicts |
| `call_tool_with_retry(tool_name, arguments, max_attempts)` | Invokes a tool with up to 3 retries on timeout/connection errors |

### orders.py

**What it does:** Orders domain MCP client. Extends `BaseMCPClient` to connect to the Orders MCP server. Wraps four tools (`search_orders_v1`, `get_order_details_v1`, `refund_order_v1`, `cancel_order_v1`) with Redis caching on reads and cache invalidation on writes. Passes JWT `token` to the server for authorization.

**Imports:**

| Import | Why we need it |
|--------|----------------|
| `mcp_clients.base.BaseMCPClient` | Base connection and retry logic |
| `db.redis.redis_cache` | Caches order details (300s TTL) |
| `config.settings` | Reads `ORDERS_MCP_URL` |
| `json` | Parses tool response JSON |

**Class `OrdersMCPClient` methods:**

| Name | What it does |
|------|--------------|
| `get_order_details(tenant_id, token, order_id)` | Fetches order with Redis cache; calls `get_order_details_v1` |
| `search_orders(tenant_id, token, user_id)` | Lists orders; calls `search_orders_v1` |
| `refund_order(tenant_id, token, order_id, reason)` | Refunds order, invalidates cache; calls `refund_order_v1` |
| `cancel_order(tenant_id, token, order_id, reason)` | Cancels order, invalidates cache; calls `cancel_order_v1` |
| `orders_mcp_client` | Module-level singleton |

### crm.py

**What it does:** CRM domain MCP client. Wraps three tools (`get_customer`, `update_customer`, `customer_notes`) with Redis caching on reads. Does not pass JWT tokens—CRM MCP has no auth layer.

**Imports:**

| Import | Why we need it |
|--------|----------------|
| `mcp_clients.base.BaseMCPClient` | Base connection and retry logic |
| `db.redis.redis_cache` | Caches customer profiles (300s TTL) |
| `config.settings` | Reads `CRM_MCP_URL` |
| `json` | Parses tool response JSON |

**Class `CRMMCPClient` methods:**

| Name | What it does |
|------|--------------|
| `get_customer(tenant_id, customer_id)` | Fetches customer with Redis cache |
| `update_customer(tenant_id, customer_id, email, phone)` | Updates contact info, invalidates cache |
| `customer_notes(tenant_id, customer_id, note)` | Appends a note, invalidates cache |
| `crm_mcp_client` | Module-level singleton |

### tickets.py

**What it does:** Tickets domain MCP client. Wraps three tools (`create_ticket`, `search_ticket`, `update_ticket`). No Redis caching and no JWT—Tickets MCP has no auth layer.

**Imports:**

| Import | Why we need it |
|--------|----------------|
| `mcp_clients.base.BaseMCPClient` | Base connection and retry logic |
| `config.settings` | Reads `TICKETS_MCP_URL` |
| `json` | Parses tool response JSON |

**Class `TicketsMCPClient` methods:**

| Name | What it does |
|------|--------------|
| `create_ticket(tenant_id, customer_id, subject, priority)` | Creates a new support ticket |
| `search_ticket(tenant_id, customer_id)` | Searches tickets, optionally filtered by customer |
| `update_ticket(tenant_id, ticket_id, status, priority)` | Updates ticket status or priority |
| `tickets_mcp_client` | Module-level singleton |

---

## backend/graph/

### Folder Summary

The `backend/graph/` folder defines the LangGraph AI agent workflow—the core intelligence of the platform. `state.py` declares `AgentState`, a TypedDict holding messages, user context (tenant, role, token, API key), and human-in-the-loop fields (`approval_required`, `pending_approval`). `tools.py` wraps MCP client calls as LangChain `@tool` functions and filters them by role via `get_tools_for_role()`. `nodes.py` implements four graph nodes: `llm_node` (calls GPT-4o with role-filtered tools), `tool_node` (executes tool calls with tenant injection and refund > $1000 interception), `approval_node` (LangGraph `interrupt()` for supervisor decisions), and `response_node` (saves the final answer to PostgreSQL). `builder.py` wires these nodes into a `StateGraph` with conditional routing and compiles it with `AsyncPostgresSaver` for checkpointing. The refund human-in-the-loop flow works as follows: `tool_node` detects amount > $1000, sets `approval_required=True`, `approval_node` calls `interrupt()`, the WebSocket surfaces an approval prompt, and resumption continues execution after the supervisor decides.

### state.py

**What it does:** Defines the `AgentState` TypedDict that LangGraph uses to pass data between nodes. Includes message history, user identity, JWT token, per-session OpenAI API key, tool call tracking, and human-in-the-loop approval fields.

**Imports:**

| Import | Why we need it |
|--------|----------------|
| `typing.TypedDict, Annotated, Sequence, Optional, List, Dict, Any` | Type definitions for state fields |
| `langgraph.graph.message.add_messages` | Reducer that appends messages to the history |
| `langchain_core.messages.BaseMessage` | Message type for the conversation |

**Types:**

| Name | What it does |
|------|--------------|
| `AgentState` | TypedDict with fields: `messages`, `user_id`, `tenant_id`, `role`, `token`, `openai_api_key`, `tool_calls`, `tool_results`, `approval_required`, `current_step`, `final_answer`, `conversation_id`, `pending_approval` |

### tools.py

**What it does:** Defines 10 LangChain `@tool` functions that wrap MCP client calls for orders, CRM, and tickets. Each tool returns JSON strings. `ALL_TOOLS` lists every tool; `get_tools_for_role()` filters by the user's role using `ROLE_PERMISSIONS`.

**Imports:**

| Import | Why we need it |
|--------|----------------|
| `langchain_core.tools.tool` | Decorator that registers functions as LLM-callable tools |
| `mcp_clients.orders/crm/tickets` | Domain MCP client singletons |
| `json` | Serializes MCP responses to JSON strings |

**Tools / functions:**

| Name | What it does |
|------|--------------|
| `search_orders_v1` | Search orders for a tenant |
| `get_order_details_v1` | Get details for a specific order |
| `refund_order_v1` | Request a refund (>$1000 triggers human approval) |
| `cancel_order_v1` | Cancel an order before shipment |
| `get_customer` | Retrieve customer profile |
| `update_customer` | Update customer email/phone |
| `customer_notes` | Append a note to customer profile |
| `create_ticket` | Create a new support ticket |
| `search_ticket` | Search support tickets |
| `update_ticket` | Update ticket status or priority |
| `ALL_TOOLS` | Master list of all 10 tool functions |
| `get_tools_for_role(role)` | Returns tools filtered by role permissions |

### nodes.py

**What it does:** Implements the four LangGraph node functions and the routing logic. `llm_node` calls GPT-4o with streaming and role-filtered tools. `tool_node` executes tool calls, injects tenant/token, intercepts refunds > $1000, and logs executions to PostgreSQL. `approval_node` triggers LangGraph `interrupt()` and processes the supervisor's decision. `response_node` saves the final assistant message. `router_node` decides the next node based on message type and approval state.

**Imports:**

| Import | Why we need it |
|--------|----------------|
| `langchain_openai.ChatOpenAI` | OpenAI GPT-4o LLM with streaming |
| `langchain_core.messages.AIMessage, ToolMessage, HumanMessage` | Message types for the conversation |
| `langgraph.types.interrupt` | Pauses graph for human-in-the-loop |
| `graph.state.AgentState` | State type definition |
| `graph.tools.get_tools_for_role` | Role-filtered tool list |
| `db.postgres.postgres_db` | Audit logging and message persistence |
| `config.settings` | Fallback OpenAI API key from environment |

**Functions:**

| Name | What it does |
|------|--------------|
| `_get_llm(api_key)` | Creates ChatOpenAI instance; prefers per-session key from WebSocket |
| `llm_node(state)` | Invokes LLM with role-filtered tools bound; returns AIMessage |
| `tool_node(state)` | Executes tool calls, intercepts refunds > $1000, logs to DB |
| `approval_node(state)` | Calls `interrupt()`, processes approve/deny on resume |
| `response_node(state)` | Saves final assistant message to PostgreSQL |
| `router_node(state)` | Returns next node name: `tools`, `approval`, `llm`, or `response` |

### builder.py

**What it does:** Compiles the LangGraph `StateGraph` workflow. Sets up `AsyncPostgresSaver` checkpointer (normalizing the connection URL), adds four nodes, defines conditional edges via `router_node`, and compiles the graph. Called once at backend startup.

**Imports:**

| Import | Why we need it |
|--------|----------------|
| `langgraph.graph.StateGraph, START, END` | Graph construction primitives |
| `langgraph.checkpoint.postgres.aio.AsyncPostgresSaver` | Persists graph state to PostgreSQL |
| `config.settings` | Reads `POSTGRES_URL` |
| `graph.state.AgentState` | State type for the graph |
| `graph.nodes.*` | Node functions and router |

**Class `GraphBuilder` methods:**

| Name | What it does |
|------|--------------|
| `initialize()` | Creates PostgresSaver, builds StateGraph with nodes/edges, compiles with checkpointer |
| `cleanup()` | Placeholder for checkpointer resource cleanup |
| `graph_builder` | Module-level singleton |

---

## mcp_servers/

### Folder Summary (overview of all 3 servers)

The `mcp_servers/` folder contains three independent MCP servers, each owning a business domain: orders, CRM, and tickets. All three are built with **FastMCP** and expose their MCP endpoint at `/mcp` using the **streamable-http** transport. Each server is a self-contained Python application with its own `Dockerfile`, `requirements.txt`, `server.py` (tool/resource/prompt definitions), and `db.py` (in-memory mock database). The Orders MCP (port 8001) is the only server with JWT authentication—it validates tokens and enforces role-based tool permissions via `auth.py`, and uses Redis for order detail caching. The CRM MCP (port 8002) and Tickets MCP (port 8003) do not require JWT tokens; they rely on `tenant_id` parameters for data isolation. Each server exposes domain-specific `@mcp.tool()` functions that return JSON strings, plus `@mcp.resource()` and `@mcp.prompt()` definitions for read-only data and templates. The backend connects to all three via `streamable_http_client` at startup and invokes tools on behalf of the LangGraph agent.

---

## mcp_servers/orders/

### Folder Summary

The Orders MCP server handles all order-related operations: searching, viewing details, refunding, and canceling. It runs on port 8001 with **JWT authentication**—every tool call must include a valid `token` that is decoded and checked against the user's role and tenant. `auth.py` mirrors the backend's permission model (admin gets all four tools, support gets three, viewer gets two read-only tools). `db.py` provides an in-memory mock database with sample orders for `tenant_a` and `tenant_b`, including `ord_102` ($1,200) which triggers the human-in-the-loop refund flow. `server.py` defines four tools, one resource (`orders://refund-policy`), and one prompt (`executive_summary`), plus Redis caching for `get_order_details_v1`. The server is started with `mcp.run(transport="streamable-http")`, exposing the MCP protocol at `/mcp`.

### server.py

**What it does:** FastMCP server for the orders domain. Defines four tools (search, get details, refund, cancel), one resource (refund policy document), and one prompt (executive summary). Validates JWT tokens and enforces role permissions on every tool call. Uses Redis for caching order details.

**Imports:**

| Import | Why we need it |
|--------|----------------|
| `mcp.server.fastmcp.FastMCP` | FastMCP server framework |
| `redis` | Synchronous Redis client for order caching |
| `db.orders_db` | In-memory mock orders database |
| `auth.decode_token, verify_tool_permission` | JWT validation and role checks |
| `json` | Serializes tool responses |
| `os` | Reads `REDIS_URL` and `PORT` environment variables |

**Functions:**

| Name | What it does |
|------|--------------|
| `authorize(token, tool_name, requested_tenant)` | Decodes JWT, checks tenant match and role permission |
| `search_orders_v1(tenant_id, token, user_id)` | MCP tool — lists orders for a tenant |
| `get_order_details_v1(tenant_id, token, order_id)` | MCP tool — fetches order with Redis cache |
| `refund_order_v1(tenant_id, token, order_id, reason)` | MCP tool — refunds an order, invalidates cache |
| `cancel_order_v1(tenant_id, token, order_id, reason)` | MCP tool — cancels an order, invalidates cache |
| `refund_policy()` | MCP resource at `orders://refund-policy` — returns refund policy text |
| `executive_summary(order_id)` | MCP prompt — generates an executive summary template |

### auth.py

**What it does:** JWT authentication helpers for the Orders MCP server. Decodes tokens using the shared `JWT_SECRET` and verifies that the caller's role is permitted to invoke a specific tool. Only used by the Orders server—CRM and Tickets have no auth.

**Imports:**

| Import | Why we need it |
|--------|----------------|
| `jose.jwt, JWTError` | JWT decoding |
| `os` | Reads `JWT_SECRET` environment variable |

**Functions:**

| Name | What it does |
|------|--------------|
| `decode_token(token)` | Decodes and validates JWT; returns claims dict or `None` |
| `verify_tool_permission(role, tool_name)` | Checks if role is in the allowed tools list for Orders |

### db.py

**What it does:** In-memory mock orders database. Stores orders keyed by `tenant_id` then `order_id`. Includes sample data for `tenant_a` (4 orders) and `tenant_b` (2 orders). Simulates async DB latency with `asyncio.sleep()`.

**Imports:**

| Import | Why we need it |
|--------|----------------|
| `asyncio` | Simulates network/DB latency |
| `typing.Dict, List, Optional` | Type hints |

**Class `OrdersDB` methods:**

| Name | What it does |
|------|--------------|
| `search_orders(tenant_id, user_id)` | Returns all orders for tenant, optionally filtered by user |
| `get_order_details(tenant_id, order_id)` | Returns a single order dict or `None` |
| `refund_order(tenant_id, order_id, reason)` | Sets order status to `refunded` |
| `cancel_order(tenant_id, order_id, reason)` | Sets order status to `cancelled` |
| `orders_db` | Module-level singleton with seed data |

### Dockerfile

**What it does:** Builds the Orders MCP Docker image. Python 3.11 slim, installs `mcp[cli]`, `python-jose`, `redis`, exposes port 8001, runs `python server.py`.

| Step | What it does |
|------|--------------|
| `FROM python:3.11-slim` | Base Python image |
| `pip install -r requirements.txt` | Installs MCP, JWT, Redis dependencies |
| `CMD ["python", "server.py"]` | Starts FastMCP with streamable-http on port 8001 |

### requirements.txt

**What it does:** Python dependencies for the Orders MCP server.

| Package | Why we need it |
|---------|----------------|
| `mcp[cli]>=1.0.0` | FastMCP server framework with CLI |
| `python-jose[cryptography]>=3.3.0` | JWT token decoding |
| `redis>=5.0.1` | Order detail caching |
| `pydantic>=2.0` | Data validation (used by FastMCP) |
| `uvicorn>=0.23.0` | ASGI server for streamable-http transport |

---

## mcp_servers/crm/

### Folder Summary

The CRM MCP server manages customer relationship data: retrieving profiles, updating contact information, and appending notes. It runs on port 8002 and does **not** require JWT authentication—tools are called with only `tenant_id` and `customer_id` parameters, and tenant isolation is enforced at the database layer. `db.py` holds an in-memory mock CRM database with five customers across `tenant_a` and `tenant_b`, including tier levels, contact info, notes, and purchase history. `server.py` defines three tools (`get_customer`, `update_customer`, `customer_notes`) and two resources (`crm://customer-profile/{customer_id}` and `crm://customer-history/{customer_id}`) that provide read-only customer data. The server uses FastMCP with `streamable-http` transport at `/mcp`, matching the URL configured in the backend's `CRM_MCP_URL` environment variable.

### server.py

**What it does:** FastMCP server for the CRM domain. Defines three tools for customer CRUD operations and two resources for read-only profile and history lookups. No JWT authentication required.

**Imports:**

| Import | Why we need it |
|--------|----------------|
| `mcp.server.fastmcp.FastMCP` | FastMCP server framework |
| `db.crm_db` | In-memory mock CRM database |
| `json` | Serializes tool responses |
| `os` | Reads `PORT` environment variable |

**Functions:**

| Name | What it does |
|------|--------------|
| `get_customer(tenant_id, customer_id)` | MCP tool — retrieves customer profile |
| `update_customer(tenant_id, customer_id, email, phone)` | MCP tool — updates contact information |
| `customer_notes(tenant_id, customer_id, note)` | MCP tool — appends a note to customer profile |
| `customer_profile(customer_id)` | MCP resource — returns formatted profile across tenants |
| `customer_history(customer_id)` | MCP resource — returns purchase history across tenants |

### db.py

**What it does:** In-memory mock CRM database. Stores customers keyed by `tenant_id` then `customer_id` with fields for name, email, phone, tier, notes, and purchase history.

**Imports:**

| Import | Why we need it |
|--------|----------------|
| `asyncio` | Simulates DB latency |
| `typing.Dict, Optional, List` | Type hints |

**Class `CRMDB` methods:**

| Name | What it does |
|------|--------------|
| `get_customer(tenant_id, customer_id)` | Returns customer dict or `None` |
| `update_customer(tenant_id, customer_id, updates)` | Updates email, phone, name, or tier |
| `add_customer_note(tenant_id, customer_id, note)` | Appends a note to the customer's notes field |
| `crm_db` | Module-level singleton with seed data |

### Dockerfile

**What it does:** Builds the CRM MCP Docker image. Python 3.11 slim, exposes port 8002, runs `python server.py`.

| Step | What it does |
|------|--------------|
| `FROM python:3.11-slim` | Base Python image |
| `pip install -r requirements.txt` | Installs MCP dependencies |
| `CMD ["python", "server.py"]` | Starts FastMCP with streamable-http on port 8002 |

### requirements.txt

**What it does:** Python dependencies for the CRM MCP server (no JWT or Redis needed).

| Package | Why we need it |
|---------|----------------|
| `mcp[cli]>=1.0.0` | FastMCP server framework |
| `pydantic>=2.0` | Data validation |
| `uvicorn>=0.23.0` | ASGI server for streamable-http transport |

---

## mcp_servers/tickets/

### Folder Summary

The Tickets MCP server handles support ticket lifecycle: creating new tickets, searching existing ones, and updating status or priority. It runs on port 8003 and, like CRM, does **not** require JWT authentication—only `tenant_id` is needed for data isolation. `db.py` provides an in-memory mock database with sample tickets for both tenants and generates new ticket IDs randomly. `server.py` defines three tools (`create_ticket`, `search_ticket`, `update_ticket`) and one resource (`tickets://templates`) that returns JSON templates for common support scenarios like refund requests, shipping delays, and technical support. The server starts with `mcp.run(transport="streamable-http")`, making the MCP endpoint available at `http://tickets_mcp:8003/mcp` within the Docker network.

### server.py

**What it does:** FastMCP server for the tickets domain. Defines three tools for ticket CRUD and one resource with support ticket templates. No JWT authentication required.

**Imports:**

| Import | Why we need it |
|--------|----------------|
| `mcp.server.fastmcp.FastMCP` | FastMCP server framework |
| `db.tickets_db` | In-memory mock tickets database |
| `json` | Serializes tool responses and template resource |
| `os` | Reads `PORT` environment variable |

**Functions:**

| Name | What it does |
|------|--------------|
| `create_ticket(tenant_id, customer_id, subject, priority)` | MCP tool — creates a new support ticket |
| `search_ticket(tenant_id, customer_id)` | MCP tool — searches tickets, optionally by customer |
| `update_ticket(tenant_id, ticket_id, status, priority)` | MCP tool — updates ticket status or priority |
| `ticket_templates()` | MCP resource at `tickets://templates` — returns JSON templates for common issues |

### db.py

**What it does:** In-memory mock tickets database. Stores tickets keyed by `tenant_id` then `ticket_id`. Generates random ticket IDs for new tickets.

**Imports:**

| Import | Why we need it |
|--------|----------------|
| `asyncio` | Simulates DB latency |
| `random` | Generates random ticket IDs |
| `typing.Dict, Optional, List` | Type hints |

**Class `TicketsDB` methods:**

| Name | What it does |
|------|--------------|
| `create_ticket(tenant_id, customer_id, subject, priority)` | Creates a new ticket with random ID |
| `search_tickets(tenant_id, customer_id)` | Returns tickets for tenant, optionally filtered by customer |
| `update_ticket(tenant_id, ticket_id, status, priority)` | Updates ticket status and/or priority |
| `tickets_db` | Module-level singleton with seed data |

### Dockerfile

**What it does:** Builds the Tickets MCP Docker image. Python 3.11 slim, exposes port 8003, runs `python server.py`.

| Step | What it does |
|------|--------------|
| `FROM python:3.11-slim` | Base Python image |
| `pip install -r requirements.txt` | Installs MCP dependencies |
| `CMD ["python", "server.py"]` | Starts FastMCP with streamable-http on port 8003 |

### requirements.txt

**What it does:** Python dependencies for the Tickets MCP server.

| Package | Why we need it |
|---------|----------------|
| `mcp[cli]>=1.0.0` | FastMCP server framework |
| `pydantic>=2.0` | Data validation |
| `uvicorn>=0.23.0` | ASGI server for streamable-http transport |

---

## frontend/

### Folder Summary

The `frontend/` folder contains the Streamlit chat application that users interact with. `app.py` is the main UI: it provides a sidebar for entering the OpenAI API key (stored only in the browser session), selecting a demo user profile (matching the seed users in `db/init.sql`), and obtaining a JWT token from the backend's `/api/token` endpoint. The chat area connects to the backend via WebSocket using `ws_client.py`, which sends `user_message` payloads containing the message content, `thread_id`, and `openai_api_key`. As the LangGraph agent runs, the UI renders streaming events—thinking indicators, tool execution boxes, token-by-token responses, and human approval prompts for refunds over $1,000. When an approval is needed, the UI shows Approve/Deny buttons that send an `approval_response` over WebSocket. `Dockerfile` and `requirements.txt` package the app for Docker Compose on port 8501.

### app.py

**What it does:** Streamlit chat application. Provides sidebar for OpenAI API key entry, demo user login (JWT token generation), and thread management. Renders chat history, streams agent responses in real time, and displays human-in-the-loop approval UI for high-value refunds.

**Imports:**

| Import | Why we need it |
|--------|----------------|
| `streamlit` (as `st`) | Web UI framework |
| `asyncio` | Runs async WebSocket client functions |
| `requests` | Calls backend `POST /api/token` for JWT generation |
| `uuid` | Generates unique conversation thread IDs |
| `os` | Reads `BACKEND_URL` and `OPENAI_API_KEY` from environment |
| `ws_client.stream_ws_chat, send_ws_approval` | WebSocket streaming helpers |

**Key functions / UI blocks:**

| Name | What it does |
|------|--------------|
| Sidebar: API key input | Stores `openai_api_key` in session state; sent in every WebSocket message |
| Sidebar: user selectbox + login button | Calls `/api/token`, stores JWT and user context in session state |
| `run_chat_stream(content)` | Sends user message over WebSocket, renders streaming events (thinking, tools, tokens, approval, final) |
| `run_approval_stream(approved)` | Sends approval decision over WebSocket, streams completion events |
| `render_messages()` | Displays chat history from session state |
| Approval UI (Approve/Deny buttons) | Shown when `human_approval` event received; triggers `run_approval_stream` |

### ws_client.py

**What it does:** Async WebSocket client helpers for the Streamlit frontend. Connects to the backend at `ws://backend:8000/ws/chat?token=...`, sends JSON message payloads, and yields streaming events as an async generator.

**Imports:**

| Import | Why we need it |
|--------|----------------|
| `websockets` | Async WebSocket client library |
| `json` | Serializes/deserializes message payloads |
| `asyncio` | Async runtime (implicit via async generators) |
| `logging` | Logs connection events and errors |

**Functions:**

| Name | What it does |
|------|--------------|
| `stream_ws_chat(backend_url, token, thread_id, content, openai_api_key)` | Connects WS, sends `user_message` with optional `openai_api_key`, yields events until `final` |
| `send_ws_approval(backend_url, token, thread_id, approved, openai_api_key)` | Connects WS, sends `approval_response` with optional `openai_api_key`, yields events until `final` |

### Dockerfile

**What it does:** Builds the Streamlit frontend Docker image. Python 3.11 slim, exposes port 8501, runs Streamlit server bound to `0.0.0.0`.

| Step | What it does |
|------|--------------|
| `FROM python:3.11-slim` | Base Python image |
| `pip install -r requirements.txt` | Installs Streamlit, websockets, requests |
| `CMD ["streamlit", "run", "app.py", ...]` | Starts Streamlit on port 8501 |

### requirements.txt

**What it does:** Python dependencies for the Streamlit frontend.

| Package | Why we need it |
|---------|----------------|
| `streamlit>=1.31.0` | Web UI framework |
| `websockets>=12.0` | Async WebSocket client for chat streaming |
| `requests>=2.31.0` | HTTP client for JWT token generation |
| `python-jose[cryptography]>=3.3.0` | JWT handling (available if needed client-side) |

---

## tests/

### Folder Summary

The `tests/` folder contains pytest test suites that validate core platform behavior without requiring the full Docker stack. `conftest.py` adds the `backend/` directory to `sys.path` so test files can import backend modules directly, and configures the `anyio` backend for async tests. `test_auth.py` verifies JWT token creation/decoding and role-based permission checks for all three roles (`admin`, `support`, `viewer`). `test_mcp_servers.py` tests the in-memory mock databases in each MCP server (`orders/db.py`, `crm/db.py`, `tickets/db.py`) for tenant isolation, CRUD operations, and data integrity. `test_tools.py` validates that `get_tools_for_role()` returns the correct subset of LangChain tools for each role. Run tests with `pytest tests/ -v` from the repo root.

### conftest.py

**What it does:** Pytest configuration file. Adds `backend/` to `sys.path` for imports and sets the async test backend to `asyncio`.

**Imports:**

| Import | Why we need it |
|--------|----------------|
| `sys, os` | Manipulates Python path to include backend directory |
| `pytest` | Test framework |

**Fixtures:**

| Name | What it does |
|------|--------------|
| `anyio_backend()` | Session-scoped fixture returning `"asyncio"` for async test support |

### test_auth.py

**What it does:** Tests JWT authentication and role-based permissions. Verifies token generation/decoding preserves claims, and that `has_permission()` and `filter_permitted_tools()` enforce the correct role boundaries.

**Imports:**

| Import | Why we need it |
|--------|----------------|
| `auth.jwt_handler.create_access_token, decode_token` | JWT functions under test |
| `auth.permissions.has_permission, filter_permitted_tools` | Permission functions under test |
| `datetime.timedelta` | Sets short token expiry for test |

**Test functions:**

| Name | What it does |
|------|--------------|
| `test_jwt_generation_and_decoding()` | Creates a token, decodes it, asserts claims match |
| `test_role_permissions()` | Asserts admin/support/viewer can/cannot call specific tools |
| `test_filter_permitted_tools()` | Asserts support role filters out `refund_order_v1` from tool list |

### test_mcp_servers.py

**What it does:** Tests the in-memory mock databases for all three MCP servers. Dynamically imports `db.py` from each server folder. Validates tenant isolation, CRUD operations, and data integrity.

**Imports:**

| Import | Why we need it |
|--------|----------------|
| `importlib.util` | Dynamically loads MCP server db modules by file path |
| `pytest` | Test framework with `@pytest.mark.asyncio` |

**Test functions:**

| Name | What it does |
|------|--------------|
| `test_orders_db_search_and_refund()` | Searches tenant_a orders, verifies isolation, tests refund |
| `test_crm_db()` | Fetches customer, adds note, verifies update |
| `test_tickets_db()` | Searches tickets, creates new ticket, verifies fields |

### test_tools.py

**What it does:** Tests that `get_tools_for_role()` returns the correct tool subsets for admin, support, and viewer roles.

**Imports:**

| Import | Why we need it |
|--------|----------------|
| `graph.tools.get_tools_for_role, ALL_TOOLS` | Tool filtering functions under test |

**Test functions:**

| Name | What it does |
|------|--------------|
| `test_get_tools_for_role()` | Asserts admin gets all tools, support excludes refund, viewer is read-only |

---

## monitoring/

### Folder Summary

The `monitoring/` folder contains configuration for observability of the running platform. Currently it holds a single file, `prometheus.yml`, which tells the Prometheus container how to scrape metrics from the backend. Prometheus runs on port 9090 (defined in `docker-compose.yml`) and polls the backend's `/metrics` endpoint every 15 seconds. The backend exposes counters for tool calls and failures, a latency histogram, and a gauge for active WebSocket sessions—all defined in `backend/api/metrics.py`. This setup gives you a foundation for monitoring agent behavior in production: you can see which tools are called most often, how long they take, and how many chat sessions are active. To view metrics, open http://localhost:9090 after starting the stack.

### prometheus.yml

**What it does:** Prometheus scrape configuration. Defines a single job `support-backend` that scrapes `backend:8000/metrics` every 15 seconds.

**Configuration blocks:**

| Block | What it does |
|-------|--------------|
| `global.scrape_interval: 15s` | How often Prometheus collects metrics |
| `global.evaluation_interval: 15s` | How often recording/alerting rules are evaluated |
| `scrape_configs[0].job_name: support-backend` | Names the scrape job for the backend service |
| `scrape_configs[0].metrics_path: /metrics` | Backend endpoint exposing Prometheus metrics |
| `scrape_configs[0].targets: [backend:8000]` | Docker network hostname and port of the backend |
