"""Tests for main app endpoints (health, root)"""

import pytest
from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    """Test the health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_endpoint(client: TestClient):
    """Test the root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Oiduna API"
    assert "docs" in data
    assert "health" in data
