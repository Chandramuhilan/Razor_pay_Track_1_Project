"""
Integration tests for FastAPI endpoints and complete end-to-end commerce flow.
"""

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_mcp_tools_endpoint():
    response = client.get("/api/mcp/tools")
    assert response.status_code == 200
    data = response.json()
    assert "tools" in data
    assert len(data["tools"]) >= 4

def test_ucp_catalog_endpoint():
    response = client.get("/api/catalog")
    assert response.status_code == 200
    data = response.json()
    assert data["merchant_id"] == "merchant_techverse_01"
    assert len(data["items"]) >= 3

def test_run_autonomous_flow_success():
    payload = {
        "user_query": "I need a laptop for programming under ₹70,000.",
        "max_budget_inr": 70000.00
    }
    response = client.post("/api/commerce/run-flow", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["cart"]["total_amount_inr"] == 67999.0
    assert data["upsell_details"]["accepted"] is True
    assert data["receipt"]["order_id"] is not None

def test_run_autonomous_flow_budget_too_low():
    # Budget of 50 INR, below all catalog items -> 404 No Products Found
    payload = {
        "user_query": "I need a 65W GaN fast charger under ₹50.",
        "max_budget_inr": 50.00
    }
    response = client.post("/api/commerce/run-flow", json=payload)
    assert response.status_code == 404
