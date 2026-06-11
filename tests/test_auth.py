import sys
import os
import pytest
from datetime import timedelta

# Ensure backend modules can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from auth.jwt_handler import create_access_token, decode_token
from auth.permissions import has_permission, filter_permitted_tools

def test_jwt_generation_and_decoding():
    user_id = "user_test_1"
    tenant_id = "tenant_test"
    role = "support"
    
    token = create_access_token(user_id, tenant_id, role, expires_delta=timedelta(minutes=5))
    assert token is not None
    assert isinstance(token, str)
    
    claims = decode_token(token)
    assert claims is not None
    assert claims["user_id"] == user_id
    assert claims["tenant_id"] == tenant_id
    assert claims["role"] == role

def test_role_permissions():
    # Admin permissions
    assert has_permission("admin", "refund_order_v1") is True
    assert has_permission("admin", "search_orders_v1") is True
    assert has_permission("admin", "create_ticket") is True
    
    # Support permissions
    assert has_permission("support", "refund_order_v1") is False
    assert has_permission("support", "search_orders_v1") is True
    assert has_permission("support", "create_ticket") is True
    
    # Viewer permissions
    assert has_permission("viewer", "refund_order_v1") is False
    assert has_permission("viewer", "search_orders_v1") is True
    assert has_permission("viewer", "create_ticket") is False

def test_filter_permitted_tools():
    tools = [
        {"name": "search_orders_v1"},
        {"name": "refund_order_v1"},
        {"name": "create_ticket"},
    ]
    
    # Support role should filter out refund_order_v1
    filtered = filter_permitted_tools("support", tools)
    tool_names = {t["name"] for t in filtered}
    assert "search_orders_v1" in tool_names
    assert "create_ticket" in tool_names
    assert "refund_order_v1" not in tool_names
