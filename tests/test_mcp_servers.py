import sys
import os
import pytest
import importlib.util

def import_module_from_path(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# Resolve db modules dynamically
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
orders_db_mod = import_module_from_path("orders_db_mod", os.path.join(base_dir, "mcp_servers", "orders", "db.py"))
crm_db_mod = import_module_from_path("crm_db_mod", os.path.join(base_dir, "mcp_servers", "crm", "db.py"))
tickets_db_mod = import_module_from_path("tickets_db_mod", os.path.join(base_dir, "mcp_servers", "tickets", "db.py"))

orders_db = orders_db_mod.orders_db
crm_db = crm_db_mod.crm_db
tickets_db = tickets_db_mod.tickets_db


@pytest.mark.asyncio
async def test_orders_db_search_and_refund():
    # Test searching orders
    orders = await orders_db.search_orders("tenant_a")
    assert len(orders) > 0
    assert any(o["id"] == "ord_101" for o in orders)
    
    # Test tenant isolation (tenant_b orders should not show up in tenant_a search)
    assert not any(o["id"] == "ord_201" for o in orders)
    
    # Test getting details
    order = await orders_db.get_order_details("tenant_a", "ord_101")
    assert order is not None
    assert order["amount"] == 150.00
    
    # Test refund
    refund_res = await orders_db.refund_order("tenant_a", "ord_101", "damaged item")
    assert refund_res["status"] == "success"
    assert refund_res["order"]["status"] == "refunded"

@pytest.mark.asyncio
async def test_crm_db():
    cust = await crm_db.get_customer("tenant_a", "cust_101")
    assert cust is not None
    assert cust["name"] == "Alice Johnson"
    assert cust["tier"] == "gold"
    
    # Test note additions
    res = await crm_db.add_customer_note("tenant_a", "cust_101", "called support")
    assert res["status"] == "success"
    assert "called support" in res["customer"]["notes"]

@pytest.mark.asyncio
async def test_tickets_db():
    tickets = await tickets_db.search_tickets("tenant_a")
    assert len(tickets) > 0
    
    # Create ticket
    new_t = await tickets_db.create_ticket("tenant_a", "cust_101", "Broken charger", "high")
    assert new_t["id"] is not None
    assert new_t["subject"] == "Broken charger"
    assert new_t["priority"] == "high"
