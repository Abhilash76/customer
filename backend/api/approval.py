import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from langgraph.types import Command
from db.postgres import postgres_db
from graph.builder import graph_builder

logger = logging.getLogger("backend.api.approval")
router = APIRouter()

class ApprovalPayload(BaseModel):
    thread_id: str
    approved: bool
    reviewer_id: str

@router.post("/human-approval")
async def resolve_approval(payload: ApprovalPayload):
    """Resume a paused LangGraph thread with approval response."""
    thread_id = payload.thread_id
    approved = payload.approved
    reviewer_id = payload.reviewer_id
    
    logger.info(f"Received human approval decision: approved={approved} for thread={thread_id} by {reviewer_id}")
    
    # 1. Update status in Postgres
    try:
        await postgres_db.update_approval_status(thread_id, approved, reviewer_id)
    except Exception as e:
        logger.error(f"Failed to update approval status in database: {e}")
        
    # 2. Resume graph execution
    if not graph_builder.graph:
        raise HTTPException(status_code=500, detail="LangGraph engine is not initialized.")
        
    config = {"configurable": {"thread_id": thread_id}}
    
    try:
        # Resume the graph with the Command
        # The graph will run starting from the interrupt in approval_node,
        # update state, and then execute the remaining nodes.
        state = await graph_builder.graph.aget_state(config)
        if not state.next:
            return {"status": "skipped", "message": "Thread is not currently paused."}
            
        logger.info(f"Resuming thread {thread_id}...")
        await graph_builder.graph.ainvoke(
            Command(resume={"approved": approved, "reviewer_id": reviewer_id}),
            config=config
        )
        return {"status": "success", "message": "Graph successfully resumed."}
    except Exception as e:
        logger.error(f"Error resuming graph for thread {thread_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to resume graph: {str(e)}")
