import streamlit as st
import asyncio
import requests
import uuid
import os
from ws_client import stream_ws_chat, send_ws_approval

# Page Config
st.set_page_config(
    page_title="AI Agent Platform - Customer Support",
    page_icon="🤖",
    layout="wide"
)

# Custom Premium Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Elegant Dark-themed card */
    .premium-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 16px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 20px rgba(0,0,0,0.15);
    }
    .premium-header h1 {
        font-weight: 800;
        margin: 0;
        font-size: 2.5rem;
    }
    .premium-header p {
        font-weight: 300;
        opacity: 0.9;
        margin-top: 0.5rem;
    }
    
    /* Collapsible tool boxes */
    .tool-box {
        background-color: #f7fafc;
        border-left: 4px solid #4f46e5;
        padding: 10px;
        border-radius: 4px;
        margin: 5px 0;
        font-family: monospace;
        font-size: 0.85rem;
    }
    
    .thinking-box {
        color: #718096;
        font-style: italic;
        margin: 5px 0;
    }
    
    /* Badge styling */
    .role-badge {
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        color: white;
        display: inline-block;
    }
    .badge-admin { background-color: #e53e3e; }
    .badge-support { background-color: #dd6b20; }
    .badge-viewer { background-color: #4a5568; }
</style>
""", unsafe_allow_value=True)

# App Title Banner
st.markdown("""
<div class="premium-header">
    <h1>Production-Grade Support Agent</h1>
    <p>Powered by LangGraph, MCP, & WebSocket Streaming</p>
</div>
""", unsafe_allow_html=True)

# Configuration from ENV
BACKEND_WS_URL = os.getenv("BACKEND_URL", "ws://backend:8000/ws/chat")
BACKEND_HTTP_URL = BACKEND_WS_URL.replace("ws://", "http://").replace("/ws/chat", "")

# Initialize session states
if "token" not in st.session_state:
    st.session_state.token = None
if "role" not in st.session_state:
    st.session_state.role = None
if "tenant_id" not in st.session_state:
    st.session_state.tenant_id = None
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "thread_id" not in st.session_state:
    st.session_state.thread_id = "thread_demo_1"
if "messages" not in st.session_state:
    st.session_state.messages = []
if "approval_request" not in st.session_state:
    st.session_state.approval_request = None
if "openai_api_key" not in st.session_state:
    st.session_state.openai_api_key = os.getenv("OPENAI_API_KEY", "")

# Sidebar Authentication panel
with st.sidebar:
    st.markdown("### 🤖 OpenAI API Key")
    st.caption("Required for the AI agent. Stored only in your browser session — never saved on the server.")
    api_key_input = st.text_input(
        "OpenAI API Key",
        value=st.session_state.openai_api_key,
        type="password",
        placeholder="sk-...",
        help="Get a key at platform.openai.com. Alternatively set OPENAI_API_KEY in .env for the backend.",
    )
    if api_key_input != st.session_state.openai_api_key:
        st.session_state.openai_api_key = api_key_input.strip()

    st.markdown("### 🔑 Authentication & Tenancy")
    
    # Selection of demo users
    user_opts = {
        "Alice Admin (Tenant A - admin)": {"id": "user_admin_1", "tenant": "tenant_a", "role": "admin"},
        "Bob Support (Tenant A - support)": {"id": "user_support_1", "tenant": "tenant_a", "role": "support"},
        "Charlie Viewer (Tenant A - viewer)": {"id": "user_viewer_1", "tenant": "tenant_a", "role": "viewer"},
        "Dave Admin (Tenant B - admin)": {"id": "user_admin_2", "tenant": "tenant_b", "role": "admin"},
        "Eve Support (Tenant B - support)": {"id": "user_support_2", "tenant": "tenant_b", "role": "support"},
    }
    
    selected_user = st.selectbox("Select User Profile (Demo)", list(user_opts.keys()))
    user_info = user_opts[selected_user]
    
    if st.button("Log In / Change Role", use_container_width=True):
        # Request access token from backend
        try:
            res = requests.post(f"{BACKEND_HTTP_URL}/api/token", json={
                "user_id": user_info["id"],
                "tenant_id": user_info["tenant"],
                "role": user_info["role"]
            })
            if res.status_code == 200:
                data = res.json()
                st.session_state.token = data["access_token"]
                st.session_state.user_id = user_info["id"]
                st.session_state.tenant_id = user_info["tenant"]
                st.session_state.role = user_info["role"]
                st.session_state.messages = []  # Clear previous chat
                st.session_state.approval_request = None
                st.toast(f"Logged in as {selected_user}!", icon="🔑")
            else:
                st.error("Failed to generate token from backend.")
        except Exception as e:
            st.error(f"Backend offline: {e}")
            
    # Session Details Display
    if st.session_state.token:
        role_class = f"badge-{st.session_state.role}"
        st.markdown(f"""
        <div style="background-color: #edf2f7; padding: 15px; border-radius: 8px; margin-top: 15px;">
            <b>Session active:</b><br/>
            User ID: <code>{st.session_state.user_id}</code><br/>
            Tenant: <code>{st.session_state.tenant_id}</code><br/>
            Role: <span class="role-badge {role_class}">{st.session_state.role.upper()}</span>
        </div>
        """, unsafe_allow_html=True)
        
        # Thread Selector / Creator
        st.markdown("### 💬 Conversation Thread")
        thread_input = st.text_input("Active Thread ID", value=st.session_state.thread_id)
        if thread_input != st.session_state.thread_id:
            st.session_state.thread_id = thread_input
            st.session_state.messages = []
            st.session_state.approval_request = None
            
        if st.button("New Conversation Thread", use_container_width=True):
            st.session_state.thread_id = f"thread_{uuid.uuid4().hex[:8]}"
            st.session_state.messages = []
            st.session_state.approval_request = None
            st.rerun()

# Check if user is logged in
if not st.session_state.token:
    st.info("👈 Please select a user profile in the sidebar and log in to start.")
elif not st.session_state.openai_api_key:
    st.warning("👈 Enter your OpenAI API key in the sidebar before chatting.")
else:
    # Helper to execute WebSocket stream wrapper synchronously
    async def run_chat_stream(content):
        # Create user message placeholder
        st.session_state.messages.append({"role": "user", "content": content})
        
        # Build UI containers for streaming events
        with chat_container:
            # Render previous messages first
            render_messages()
            
            # Now render the active streaming block
            with st.chat_message("assistant"):
                thinking_container = st.empty()
                tool_container = st.container()
                response_placeholder = st.empty()
                
                full_response = ""
                
                async for event in stream_ws_chat(
                    BACKEND_WS_URL,
                    st.session_state.token,
                    st.session_state.thread_id,
                    content,
                    openai_api_key=st.session_state.openai_api_key,
                ):
                    ev_type = event.get("type")
                    
                    if ev_type == "thinking":
                        thinking_container.markdown(f"🤔 *{event.get('content')}*")
                        
                    elif ev_type == "tool_start":
                        thinking_container.empty()
                        with tool_container:
                            st.info(f"🔧 Starting tool: **{event.get('tool_name')}** (args: {event.get('input')})")
                            
                    elif ev_type == "tool_result":
                        with tool_container:
                            with st.expander(f"✅ Tool Finished: {event.get('tool_name')}", expanded=False):
                                st.code(event.get("output"))
                                
                    elif ev_type == "token":
                        thinking_container.empty()
                        full_response += event.get("content", "")
                        response_placeholder.markdown(full_response)
                        
                    elif ev_type == "human_approval":
                        thinking_container.empty()
                        st.session_state.approval_request = event
                        st.session_state.messages.append({"role": "assistant", "content": full_response})
                        st.rerun()
                        
                    elif ev_type == "final":
                        thinking_container.empty()
                        final_text = event.get("content", full_response)
                        response_placeholder.markdown(final_text)
                        st.session_state.messages.append({"role": "assistant", "content": final_text})
                        st.rerun()
                        
                    elif ev_type == "error":
                        st.error(event.get("message"))
                        
    async def run_approval_stream(approved):
        """Submit approval decision and stream subsequent completion events."""
        with chat_container:
            render_messages()
            with st.chat_message("assistant"):
                thinking_container = st.empty()
                tool_container = st.container()
                response_placeholder = st.empty()
                
                full_response = ""
                st.session_state.approval_request = None
                
                async for event in send_ws_approval(
                    BACKEND_WS_URL,
                    st.session_state.token,
                    st.session_state.thread_id,
                    approved,
                    openai_api_key=st.session_state.openai_api_key,
                ):
                    ev_type = event.get("type")
                    
                    if ev_type == "thinking":
                        thinking_container.markdown(f"🤔 *{event.get('content')}*")
                    elif ev_type == "tool_start":
                        with tool_container:
                            st.info(f"🔧 Starting tool: **{event.get('tool_name')}**")
                    elif ev_type == "tool_result":
                        with tool_container:
                            with st.expander(f"✅ Tool Finished: {event.get('tool_name')}", expanded=False):
                                st.code(event.get("output"))
                    elif ev_type == "token":
                        full_response += event.get("content", "")
                        response_placeholder.markdown(full_response)
                    elif ev_type == "final":
                        final_text = event.get("content", full_response)
                        response_placeholder.markdown(final_text)
                        st.session_state.messages.append({"role": "assistant", "content": final_text})
                        st.rerun()
                    elif ev_type == "error":
                        st.error(event.get("message"))

    # Render History
    def render_messages():
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # Chat Display Layout
    chat_container = st.container()
    
    with chat_container:
        render_messages()

    # Human-in-the-loop Action Box
    if st.session_state.approval_request:
        req_data = st.session_state.approval_request.get("data", {})
        st.warning(f"⚠️ **Refund Approval Required!** Refund request for order **{req_data.get('order_id')}** of **${req_data.get('amount')}** requires manager authorization.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Approve Refund", use_container_width=True):
                asyncio.run(run_approval_stream(approved=True))
        with col2:
            if st.button("❌ Deny Refund", use_container_width=True):
                asyncio.run(run_approval_stream(approved=False))

    # User Input
    if not st.session_state.approval_request:
        if prompt := st.chat_input("Ask a question (e.g. 'Refund my latest order')"):
            asyncio.run(run_chat_stream(prompt))
