import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import settings
from logging_config import setup_logging
from db.postgres import postgres_db
from db.redis import redis_cache
from mcp_clients.orders import orders_mcp_client
from mcp_clients.crm import crm_mcp_client
from mcp_clients.tickets import tickets_mcp_client
from graph.builder import graph_builder
from auth.jwt_handler import create_access_token

# Import Routers
from api.health import router as health_router
from api.metrics import router as metrics_router
from api.approval import router as approval_router
from api.websocket import router as ws_router

# Setup structured logging
setup_logging()
logger = logging.getLogger("backend.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown lifecycles."""
    logger.info("Initializing application resources...")
    
    # 1. Connect Postgres & Redis
    await postgres_db.connect()
    await redis_cache.connect()
    
    # 2. Connect MCP Clients
    try:
        await orders_mcp_client.connect()
    except Exception as e:
        logger.error(f"Orders MCP client offline: {e}")
        
    try:
        await crm_mcp_client.connect()
    except Exception as e:
        logger.error(f"CRM MCP client offline: {e}")
        
    try:
        await tickets_mcp_client.connect()
    except Exception as e:
        logger.error(f"Tickets MCP client offline: {e}")

    # 3. Initialize LangGraph Engine with checkpointer
    await graph_builder.initialize()
    
    yield
    
    logger.info("Cleaning up application resources...")
    # Disconnect MCP clients
    await orders_mcp_client.close()
    await crm_mcp_client.close()
    await tickets_mcp_client.close()
    
    # Disconnect DBs
    await postgres_db.close()
    await redis_cache.close()

# Initialize FastAPI App
app = FastAPI(
    title="Production Customer Support Agent API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(health_router, tags=["System"])
app.include_router(metrics_router, tags=["Monitoring"])
app.include_router(approval_router, prefix="/api", tags=["Human-in-the-loop"])
app.include_router(ws_router, tags=["Chat"])

# Token Generation Helper for Demo Streamlit
class TokenRequest(BaseModel):
    user_id: str
    tenant_id: str
    role: str

@app.post("/api/token", tags=["Auth"])
async def generate_token_for_demo(req: TokenRequest):
    """Generate a JWT token for testing/demo purposes."""
    try:
        token = create_access_token(req.user_id, req.tenant_id, req.role)
        return {"access_token": token, "token_type": "bearer"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Start web server
    uvicorn.run("main:app", host="0.0.0.0", port=8000, log_config=None)
