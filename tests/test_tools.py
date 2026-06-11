import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from graph.tools import get_tools_for_role, ALL_TOOLS

def test_get_tools_for_role():
    admin_tools = get_tools_for_role("admin")
    admin_names = {t.name for t in admin_tools}
    
    assert "search_orders_v1" in admin_names
    assert "refund_order_v1" in admin_names
    assert "create_ticket" in admin_names
    
    support_tools = get_tools_for_role("support")
    support_names = {t.name for t in support_tools}
    
    assert "search_orders_v1" in support_names
    assert "refund_order_v1" not in support_names
    assert "create_ticket" in support_names
    
    viewer_tools = get_tools_for_role("viewer")
    viewer_names = {t.name for t in viewer_tools}
    
    assert "search_orders_v1" in viewer_names
    assert "refund_order_v1" not in viewer_names
    assert "create_ticket" not in viewer_names
