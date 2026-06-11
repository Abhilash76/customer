# backend/logging_config.py

> **Source:** `backend/logging_config.py`  
> **Purpose:** Configures structured JSON logging for the backend, enabling machine-readable logs with optional context fields.

---

## Imports

| Import | Library | Why used |
|--------|---------|----------|
| `logging` | stdlib | Python logging framework |
| `json` | stdlib | Serialize log records to JSON |
| `time` | stdlib | *(imported but unused in current code)* |
| `datetime` | stdlib | ISO timestamp formatting |
| `Any, Dict` | `typing` | Type hints |

---

## Class: `JSONFormatter(logging.Formatter)`

### `format(record: logging.LogRecord) -> str`

**Parameters:** `record` — standard Python log record  
**Returns:** JSON string with keys:

| Key | Source |
|-----|--------|
| `timestamp` | `record.created` (UTC ISO format) |
| `level` | `record.levelname` |
| `message` | `record.getMessage()` |
| `logger` | `record.name` |
| `tenant_id`, `user_id`, `thread_id`, `tool_name`, `latency`, `status` | Optional extra fields if present on record |
| `exception` | Stack trace if `record.exc_info` is set |

**Logic flow:** Build a dict → add optional context fields → serialize to JSON.

---

## Function: `setup_logging() -> None`

**Returns:** Nothing (mutates root logger)

**Logic flow:**
1. Get root logger, set level to `INFO`
2. Remove all existing handlers (idempotent re-setup)
3. Add a `StreamHandler` with `JSONFormatter`
4. Logs go to stdout (captured by Docker)

---

## Function: `get_logger(name: str) -> logging.Logger`

**Parameters:** `name` — logger name (e.g. `"backend.api.websocket"`)  
**Returns:** Standard `logging.Logger` instance

Convenience wrapper — most modules use `logging.getLogger()` directly instead.

---

## MCP connection

Logging is not MCP-specific, but context fields like `tool_name` and `tenant_id` help trace MCP tool calls in production log aggregators.

Example log from a tool execution:
```json
{"timestamp": "2026-06-11T12:00:00Z", "level": "INFO", "message": "Executing tool search_orders_v1...", "logger": "backend.graph.nodes", "tool_name": "search_orders_v1", "tenant_id": "tenant_a"}
```

---

## MCP novice notes

Structured JSON logs make it easy to filter "show me all `refund_order_v1` calls for `tenant_a`" in tools like Datadog or Grafana Loki.
