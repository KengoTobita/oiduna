"""Tests for main app endpoints (health, root)"""

import pytest
from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    """Test the health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ["healthy", "degraded"]
    assert "components" in data
    assert "osc" in data["components"]
    assert "midi" in data["components"]
    assert "engine" in data["components"]


def test_root_endpoint(client: TestClient):
    """Test the root endpoint (returns dashboard HTML)"""
    response = client.get("/")
    assert response.status_code == 200
    # Root endpoint now returns HTML dashboard, not JSON
    assert "text/html" in response.headers["content-type"]
    assert "<!DOCTYPE html>" in response.text
