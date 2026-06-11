import json
import logging
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from auth.jwt_handler import decode_token
from graph.builder import graph_builder
from db.postgres import postgres_db
from api.metrics import ACTIVE_SESSIONS, TOOL_CALLS_TOTAL, TOOL_LATENCY_SECONDS, TOOL_FAILURES_TOTAL

logger = logging.getLogger("backend.api.websocket")
router = APIRouter()

async def run_graph_and_stream(websocket: WebSocket, thread_id: str, tenant_id: str, user_id: str, role: str, token: str, content: str = None, resume_command: Command = None, openai_api_key: str | None = None):
    """Run LangGraph and stream output events over WebSocket."""
    config = {"configurable": {"thread_id": thread_id}}
    
    # Define state input if not resuming
    input_data = None
    if not resume_command:
        # Load conversation history or create one
        conv_id = await postgres_db.get_or_create_conversation(thread_id, user_id, tenant_id)
        
        # Save user message to PostgreSQL
        await postgres_db.save_message(
            conversation_id=conv_id,
            tenant_id=tenant_id,
            role="user",
            content=content
        )
        
        input_data = {
            "messages": [HumanMessage(content=content)],
            "user_id": user_id,
            "tenant_id": tenant_id,
            "role": role,
            "token": token,
            "openai_api_key": openai_api_key,
            "conversation_id": conv_id,
            "approval_required": False,
            "pending_approval": None
        }
    
    # We use astream_events version="v2" to get granular events
    # We pass either input_data (new run) or resume_command (resuming run)
    target_input = resume_command if resume_command is not None else input_data

    # Ensure resumed threads keep a usable API key (e.g. approval after chat pause)
    if resume_command is not None and openai_api_key:
        try:
            await graph_builder.graph.aupdate_state(
                config,
                {"openai_api_key": openai_api_key},
            )
        except Exception as e:
            logger.warning(f"Could not refresh openai_api_key on resume: {e}")

    try:
        # Stream events token-by-token and node-by-node
        async for event in graph_builder.graph.astream_events(target_input, config=config, version="v2"):
            if websocket.client_state != WebSocketState.CONNECTED:
                logger.warning("WebSocket disconnected. Aborting stream.")
                break
                
            kind = event["event"]
            
            # 1. Thinking Indicator (when LLM starts generating)
            if kind == "on_chat_model_start":
                await websocket.send_json({"type": "thinking", "content": "Analyzing request..."})
                
            # 2. Token Streaming (when model streams tokens)
            elif kind == "on_chat_model_stream":
                token_chunk = event["data"]["chunk"].content
                if token_chunk:
                    await websocket.send_json({"type": "token", "content": token_chunk})
                    
            # 3. Tool Execution Start
            elif kind == "on_tool_start":
                tool_name = event["name"]
                TOOL_CALLS_TOTAL.labels(tool_name=tool_name, tenant_id=tenant_id, status="started").inc()
                await websocket.send_json({
                    "type": "tool_start",
                    "tool_name": tool_name,
                    "input": str(event["data"].get("input", ""))
                })
                
            # 4. Tool Execution End
            elif kind == "on_tool_end":
                tool_name = event["name"]
                # Increment status success or check
                TOOL_CALLS_TOTAL.labels(tool_name=tool_name, tenant_id=tenant_id, status="success").inc()
                await websocket.send_json({
                    "type": "tool_result",
                    "tool_name": tool_name,
                    "output": str(event["data"].get("output", ""))
                })
                
    except Exception as e:
        logger.error(f"Error during graph execution/streaming: {e}", exc_info=True)
        try:
            await websocket.send_json({"type": "error", "message": f"Execution error: {str(e)}"})
        except Exception:
            pass
        return

    # Post-stream check: check if the graph hit an interrupt (approval needed)
    try:
        state = await graph_builder.graph.aget_state(config)
        if state.next:
            # We are paused at approval_node
            pending = state.values.get("pending_approval")
            if pending and state.values.get("approval_required"):
                logger.info(f"Graph execution paused. Surfacing approval request for thread {thread_id}")
                # Log approval request to Postgres for records
                await postgres_db.record_approval_request(
                    thread_id=thread_id,
                    tool_name=pending["tool_name"],
                    amount=float(pending["amount"])
                )
                
                # Send approval event to client
                await websocket.send_json({
                    "type": "human_approval",
                    "thread_id": thread_id,
                    "data": {
                        "tool_name": pending["tool_name"],
                        "order_id": pending["order_id"],
                        "amount": pending["amount"],
                        "reason": pending["reason"]
                    }
                })
                return
        
        # If successfully completed, send final signal
        await websocket.send_json({
            "type": "final",
            "content": state.values.get("final_answer", "")
        })
    except Exception as e:
        logger.error(f"Error checking post-stream state: {e}")

@router.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket):
    """WebSocket endpoint handling live chat session."""
    # Retrieve and decode JWT token from query parameters
    token = websocket.query_params.get("token")
    if not token:
        logger.warning("Connection rejected: missing authentication token.")
        await websocket.close(code=4008)
        return
        
    claims = decode_token(token)
    if not claims:
        logger.warning("Connection rejected: invalid or expired token.")
        await websocket.close(code=4008)
        return
        
    user_id = claims["user_id"]
    tenant_id = claims["tenant_id"]
    role = claims["role"]
    
    await websocket.accept()
    ACTIVE_SESSIONS.inc()
    logger.info(f"WebSocket session established for user={user_id}, tenant={tenant_id}, role={role}")
    
    try:
        while True:
            # Receive incoming message
            data_str = await websocket.receive_text()
            data = json.loads(data_str)
            msg_type = data.get("type")
            thread_id = data.get("thread_id")
            
            if not thread_id:
                await websocket.send_json({"type": "error", "message": "Missing thread_id."})
                continue
                
            if msg_type == "user_message":
                content = data.get("content", "")
                openai_api_key = data.get("openai_api_key") or None
                # Run the graph and stream events in the background
                asyncio.create_task(
                    run_graph_and_stream(
                        websocket=websocket,
                        thread_id=thread_id,
                        tenant_id=tenant_id,
                        user_id=user_id,
                        role=role,
                        token=token,
                        content=content,
                        openai_api_key=openai_api_key,
                    )
                )
            elif msg_type == "approval_response":
                approved = data.get("approved", False)
                openai_api_key = data.get("openai_api_key") or None
                # Resuming execution directly over WebSocket
                logger.info(f"Resuming thread {thread_id} via WebSocket approval_response (approved={approved})")
                await postgres_db.update_approval_status(thread_id, approved, user_id)
                
                asyncio.create_task(
                    run_graph_and_stream(
                        websocket=websocket,
                        thread_id=thread_id,
                        tenant_id=tenant_id,
                        user_id=user_id,
                        role=role,
                        token=token,
                        resume_command=Command(resume={"approved": approved, "reviewer_id": user_id}),
                        openai_api_key=openai_api_key,
                    )
                )
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user={user_id}, tenant={tenant_id}")
    except json.JSONDecodeError:
        logger.warning("Invalid JSON received over WebSocket.")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        ACTIVE_SESSIONS.dec()
