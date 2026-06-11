from fastapi import APIRouter, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

router = APIRouter()

# Define Prometheus metrics
TOOL_CALLS_TOTAL = Counter(
    "tool_calls_total",
    "Total number of tool calls executed.",
    ["tool_name", "tenant_id", "status"]
)

TOOL_FAILURES_TOTAL = Counter(
    "tool_failures_total",
    "Total number of tool execution failures.",
    ["tool_name", "error_type"]
)

TOOL_LATENCY_SECONDS = Histogram(
    "tool_latency_seconds",
    "Latency of tool execution in seconds.",
    ["tool_name"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

ACTIVE_SESSIONS = Gauge(
    "active_sessions",
    "Number of active WebSocket sessions."
)

@router.get("/metrics")
async def get_metrics():
    """Endpoint scraped by Prometheus to collect application metrics."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
