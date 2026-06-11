import asyncio
import logging
from typing import Dict, List, Optional, Any
from contextlib import AsyncExitStack
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

logger = logging.getLogger("backend.mcp_client")

class BaseMCPClient:
    def __init__(self, server_url: str, server_name: str):
        self.server_url = server_url
        self.server_name = server_name
        self.session: Optional[ClientSession] = None
        self._exit_stack = AsyncExitStack()

    async def connect(self):
        """Establish connection with the MCP server over Streamable HTTP."""
        logger.info(f"Connecting to MCP server '{self.server_name}' at {self.server_url}...")
        try:
            # Connect using Streamable HTTP transport (/mcp endpoint)
            read, write, _ = await self._exit_stack.enter_async_context(
                streamable_http_client(self.server_url)
            )
            self.session = await self._exit_stack.enter_async_context(ClientSession(read, write))
            await self.session.initialize()
            logger.info(f"Successfully connected and initialized MCP server '{self.server_name}'.")
        except Exception as e:
            logger.error(f"Failed to connect to MCP server '{self.server_name}': {e}")
            await self.close()
            raise e

    async def close(self):
        """Close connection and clean up resources."""
        logger.info(f"Closing connection to MCP server '{self.server_name}'...")
        await self._exit_stack.aclose()
        self.session = None

    async def list_tools(self) -> List[Dict[str, Any]]:
        """List all tools available on the server."""
        if not self.session:
            raise RuntimeError(f"Client '{self.server_name}' is not connected.")
        try:
            result = await self.session.list_tools()
            # Convert mcp.types.Tool objects to dicts
            return [{"name": t.name, "description": t.description, "inputSchema": t.inputSchema} for t in result.tools]
        except Exception as e:
            logger.error(f"Failed to list tools for '{self.server_name}': {e}")
            raise e

    async def call_tool_with_retry(self, tool_name: str, arguments: Dict[str, Any], max_attempts: int = 3) -> Dict[str, Any]:
        """Invoke a tool with exponential backoff retries for transient failures."""
        if not self.session:
            raise RuntimeError(f"Client '{self.server_name}' is not connected.")
            
        attempt = 0
        delay = 0.5 # initial delay
        
        while True:
            attempt += 1
            try:
                logger.info(f"Calling tool '{tool_name}' on '{self.server_name}' (attempt {attempt})...")
                result = await self.session.call_tool(tool_name, arguments)
                
                # Check for client-side tool execution errors returned in the content list
                # MCP tool responses are typically returned in result.content (list of TextContent/ImageContent)
                # Let's inspect content or convert result
                content_list = []
                for content in result.content:
                    if hasattr(content, "text"):
                        content_list.append(content.text)
                response_text = "\n".join(content_list)
                
                # If the tool result contains permission_denied or validation errors, do not retry
                if "permission_denied" in response_text or "permission violation" in response_text.lower():
                    logger.warning(f"Permission denied for '{tool_name}'. No retry.")
                    return {"status": "error", "error_type": "permission_denied", "message": response_text}
                
                # Success
                return {"status": "success", "content": response_text}
                
            except (asyncio.TimeoutError, ConnectionError) as e:
                # Retry transient network issues
                if attempt >= max_attempts:
                    logger.error(f"Failed calling '{tool_name}' on '{self.server_name}' after {max_attempts} attempts: {e}")
                    return {"status": "error", "error_type": "timeout", "message": str(e)}
                
                logger.warning(f"Transient error calling '{tool_name}' on '{self.server_name}': {e}. Retrying in {delay}s...")
                await asyncio.sleep(delay)
                delay *= 2
                
            except Exception as e:
                # Do not retry general exceptions/programming/validation errors
                logger.error(f"Non-retryable error calling '{tool_name}' on '{self.server_name}': {e}")
                return {"status": "error", "error_type": "fatal", "message": str(e)}
