import logging
from contextlib import AsyncExitStack
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from config import settings
from graph.state import AgentState
from graph.nodes import llm_node, tool_node, approval_node, response_node, router_node

logger = logging.getLogger("backend.graph.builder")

class GraphBuilder:
    def __init__(self):
        self.checkpointer = None
        self.graph = None
        self._exit_stack = AsyncExitStack()

    async def initialize(self):
        """Configure Checkpointer and Compile the StateGraph."""
        # Convert asyncpg connection string to standard postgres url for psycopg/PostgresSaver
        postgres_url = settings.POSTGRES_URL.replace("postgresql+asyncpg://", "postgresql://")
        
        logger.info("Initializing PostgresSaver checkpointer...")
        try:
            # from_conn_string returns an async context manager in current langgraph versions
            self.checkpointer = await self._exit_stack.enter_async_context(
                AsyncPostgresSaver.from_conn_string(postgres_url)
            )
            await self.checkpointer.setup()
            logger.info("Checkpointer setup successfully completed.")
        except Exception as e:
            logger.error(f"Failed to setup Checkpointer: {e}")
            raise e

        # Construct Graph
        workflow = StateGraph(AgentState)

        # Add Nodes
        workflow.add_node("llm", llm_node)
        workflow.add_node("tools", tool_node)
        workflow.add_node("approval", approval_node)
        workflow.add_node("response", response_node)

        # Set Entry Point
        workflow.set_entry_point("llm")

        # Add Edges
        # LLM routes dynamically
        workflow.add_conditional_edges(
            "llm",
            router_node,
            {
                "tools": "tools",
                "approval": "approval",
                "response": "response"
            }
        )

        # Tool node routes to check if approval is needed or back to LLM
        workflow.add_conditional_edges(
            "tools",
            router_node,
            {
                "approval": "approval",
                "llm": "llm",
                "response": "response"
            }
        )

        # Approval routes to tool execution or response depending on decision
        workflow.add_conditional_edges(
            "approval",
            router_node,
            {
                "tools": "tools",
                "llm": "llm",
                "response": "response"
            }
        )

        # Response completes the flow
        workflow.add_edge("response", END)

        # Compile
        self.graph = workflow.compile(checkpointer=self.checkpointer)
        logger.info("LangGraph workflow compiled successfully.")

    async def cleanup(self):
        """Cleanup connection resources."""
        await self._exit_stack.aclose()
        self.checkpointer = None
        self.graph = None

graph_builder = GraphBuilder()
