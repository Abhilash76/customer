import os
from typing import Dict, Optional
from jose import jwt, JWTError

JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key")
ALGORITHM = "HS256"

def decode_token(token: str) -> Optional[Dict]:
    """Decode a JWT token and extract the claims."""
    try:
        # Note: In a production app, verify the signature. For mock environment, we can decode it with verify=False or with JWT_SECRET.
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

def verify_tool_permission(role: str, tool_name: str) -> bool:
    """Check if a role is permitted to call a specific tool."""
    # admin: all tools
    # support: search_orders, get_order_details, cancel_order
    # viewer: read-only (search_orders, get_order_details)
    permissions = {
        "admin": ["search_orders_v1", "get_order_details_v1", "refund_order_v1", "cancel_order_v1"],
        "support": ["search_orders_v1", "get_order_details_v1", "cancel_order_v1"],
        "viewer": ["search_orders_v1", "get_order_details_v1"]
    }
    
    allowed_tools = permissions.get(role, [])
    return tool_name in allowed_tools
