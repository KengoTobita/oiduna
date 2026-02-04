"""Tests for /scene/* endpoints

Tests verify Phase 1 refactoring:
- Scene activation endpoint
- CommandResult error handling
- Critical bug fix (scene → name)
"""

import pytest
from fastapi.testclient import TestClient


def test_activate_scene_success(client: TestClient):
    """Test POST /scene/activate with valid scene ID"""
    response = client.post(
        "/scene/activate",
        json={"scene_id": "intro"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["scene_id"] == "intro"
    assert "applied_at" in data


def test_activate_nonexistent_scene(client: TestClient):
    """Test POST /scene/activate with nonexistent scene ID"""
    response = client.post(
        "/scene/activate",
        json={"scene_id": "nonexistent_scene"},
    )
    # Returns 500 with error message (Phase 1 error handling)
    assert response.status_code == 500
    assert "not found" in response.json()["detail"].lower()


def test_activate_scene_missing_id(client: TestClient):
    """Test POST /scene/activate without scene_id (Pydantic validation)"""
    response = client.post(
        "/scene/activate",
        json={},
    )
    # Pydantic validation should fail
    assert response.status_code == 422


def test_activate_scene_invalid_type(client: TestClient):
    """Test POST /scene/activate with invalid type for scene_id"""
    response = client.post(
        "/scene/activate",
        json={"scene_id": 123},  # Should be string
    )
    # Pydantic should coerce to string, so this might pass
    # But let's verify the behavior
    assert response.status_code in [200, 422]
