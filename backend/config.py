import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.1")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "your-secret-key")
    JWT_ALGORITHM: str = "HS256"
    
    # Databases
    POSTGRES_URL: str = os.getenv("POSTGRES_URL", "postgresql+asyncpg://user:password@postgres:5432/support")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    
    # MCP Servers
    ORDERS_MCP_URL: str = os.getenv("ORDERS_MCP_URL", "http://orders_mcp:8001/mcp")
    CRM_MCP_URL: str = os.getenv("CRM_MCP_URL", "http://crm_mcp:8002/mcp")
    TICKETS_MCP_URL: str = os.getenv("TICKETS_MCP_URL", "http://tickets_mcp:8003/mcp")
    
    # LangChain
    LANGCHAIN_TRACING_V2: bool = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
    LANGCHAIN_API_KEY: str = os.getenv("LANGCHAIN_API_KEY", "")
    LANGCHAIN_PROJECT: str = os.getenv("LANGCHAIN_PROJECT", "customer-support")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
