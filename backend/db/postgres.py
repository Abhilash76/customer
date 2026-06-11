import json
import logging
from typing import List, Optional, Dict, Any
import asyncpg
from config import settings

logger = logging.getLogger("backend.db.postgres")

class PostgresManager:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Initialize connection pool."""
        try:
            # asyncpg expects postgresql:// not SQLAlchemy-style postgresql+asyncpg://
            dsn = settings.POSTGRES_URL.replace("postgresql+asyncpg://", "postgresql://")
            self.pool = await asyncpg.create_pool(
                dsn,
                min_size=2,
                max_size=10
            )
            logger.info("Postgres connection pool created.")
        except Exception as e:
            logger.error(f"Failed to create Postgres connection pool: {e}")
            raise e

    async def close(self):
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Postgres connection pool closed.")

    async def execute(self, query: str, *args) -> str:
        """Execute a query without returning rows (INSERT/UPDATE/DELETE)."""
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query: str, *args) -> List[asyncpg.Record]:
        """Fetch multiple rows."""
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args) -> Optional[asyncpg.Record]:
        """Fetch a single row."""
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetchval(self, query: str, *args) -> Any:
        """Fetch a single scalar value."""
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)

    # Multi-tenant safe operations
    async def get_messages(self, conversation_id: str, tenant_id: str) -> List[Dict[str, Any]]:
        """Fetch all messages for a specific conversation in a tenant."""
        query = """
            SELECT m.role, m.content, m.metadata, m.created_at
            FROM messages m
            JOIN conversations c ON m.conversation_id = c.id
            WHERE c.id = $1 AND c.tenant_id = $2
            ORDER BY m.created_at ASC
        """
        records = await self.fetch(query, conversation_id, tenant_id)
        return [dict(r) for r in records]

    async def save_message(self, conversation_id: str, tenant_id: str, role: str, content: str, metadata: Optional[dict] = None) -> None:
        """Save a new message securely in a tenant's conversation."""
        # Ensure conversation exists and matches tenant
        conv_query = "SELECT id FROM conversations WHERE id = $1 AND tenant_id = $2"
        conv = await self.fetchrow(conv_query, conversation_id, tenant_id)
        if not conv:
            raise ValueError(f"Conversation {conversation_id} not found for tenant {tenant_id}.")
            
        insert_query = """
            INSERT INTO messages (conversation_id, role, content, metadata)
            VALUES ($1, $2, $3, $4)
        """
        metadata_json = json.dumps(metadata) if metadata else None
        await self.execute(insert_query, conversation_id, role, content, metadata_json)

    async def get_or_create_conversation(self, thread_id: str, user_id: str, tenant_id: str) -> str:
        """Get or create conversation mapping for thread_id."""
        query = "SELECT id FROM conversations WHERE thread_id = $1 AND tenant_id = $2"
        record = await self.fetchrow(query, thread_id, tenant_id)
        if record:
            return record["id"]
            
        conv_id = f"conv_{thread_id}"
        insert_query = """
            INSERT INTO conversations (id, user_id, tenant_id, thread_id)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (thread_id) DO UPDATE SET updated_at = CURRENT_TIMESTAMP
            RETURNING id
        """
        res = await self.fetchrow(insert_query, conv_id, user_id, tenant_id, thread_id)
        return res["id"]

    async def log_tool_execution(self, conversation_id: str, tool_name: str, input_val: str, output_val: str, latency_ms: int, status: str) -> None:
        """Log tool execution for audit trail."""
        query = """
            INSERT INTO tool_executions (conversation_id, tool_name, input, output, latency_ms, status)
            VALUES ($1, $2, $3, $4, $5, $6)
        """
        await self.execute(query, conversation_id, tool_name, input_val, output_val, latency_ms, status)

    async def record_approval_request(self, thread_id: str, tool_name: str, amount: float) -> int:
        """Record a new approval request in DB."""
        query = """
            INSERT INTO approvals (thread_id, tool_name, amount, status)
            VALUES ($1, $2, $3, 'pending')
            RETURNING id
        """
        res = await self.fetchrow(query, thread_id, tool_name, amount)
        return res["id"]

    async def update_approval_status(self, thread_id: str, approved: bool, reviewer_id: str) -> None:
        """Update the status of an approval request."""
        status_val = "approved" if approved else "denied"
        query = """
            UPDATE approvals
            SET status = $1, reviewer_id = $2, resolved_at = CURRENT_TIMESTAMP
            WHERE thread_id = $3 AND status = 'pending'
        """
        await self.execute(query, status_val, reviewer_id, thread_id)

postgres_db = PostgresManager()
