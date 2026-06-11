import json
import asyncio
import websockets
import logging

logger = logging.getLogger("frontend.ws_client")

async def stream_ws_chat(backend_url: str, token: str, thread_id: str, content: str):
    """Async generator connecting to backend WS and yielding events."""
    uri = f"{backend_url}?token={token}"
    logger.info(f"Connecting websocket to {uri} with thread {thread_id}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            # Send the user message payload
            payload = {
                "type": "user_message",
                "thread_id": thread_id,
                "content": content,
            }
            await websocket.send(json.dumps(payload))
            
            # Read streaming events from server
            async for msg_str in websocket:
                event = json.loads(msg_str)
                yield event
                
                # Exit generator when final message received
                if event.get("type") == "final":
                    break
    except Exception as e:
        logger.error(f"WebSocket client error: {e}")
        yield {"type": "error", "message": f"Connection lost: {str(e)}"}

async def send_ws_approval(backend_url: str, token: str, thread_id: str, approved: bool):
    """Send approval decision over a temporary WS connection and yield subsequent events."""
    uri = f"{backend_url}?token={token}"
    logger.info(f"Connecting websocket for approval response to {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            payload = {
                "type": "approval_response",
                "thread_id": thread_id,
                "approved": approved,
            }
            await websocket.send(json.dumps(payload))
            
            # Stream the remaining steps until final
            async for msg_str in websocket:
                event = json.loads(msg_str)
                yield event
                if event.get("type") == "final":
                    break
    except Exception as e:
        logger.error(f"WebSocket client approval error: {e}")
        yield {"type": "error", "message": f"Approval submission error: {str(e)}"}
