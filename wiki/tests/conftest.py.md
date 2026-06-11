# tests/conftest.py

> **Source:** `tests/conftest.py`  
> **Purpose:** Pytest configuration — adds the backend directory to Python path and configures async test backend.

---

## Imports

| Import | Library | Why used |
|--------|---------|----------|
| `sys, os` | stdlib | Path manipulation |
| `pytest` | `pytest` | Test framework and fixtures |

---

## Path setup

```python
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, backend_dir)
```

Allows tests to `from auth.jwt_handler import ...` without installing backend as a package.

---

## Fixture: `anyio_backend()` — session scope

**Returns:** `"asyncio"`

Tells pytest-asyncio to use asyncio as the async backend for `@pytest.mark.asyncio` tests.

---

## MCP connection

No direct MCP testing in conftest. Enables importing backend modules that depend on MCP clients (`mcp_clients`, `graph.tools`).

---

## MCP novice notes

Run tests from repo root: `pytest tests/ -v`. The path hack is common in monorepos where backend isn't a published package.
