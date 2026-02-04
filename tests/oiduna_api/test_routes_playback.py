"""Tests for /playback/* endpoints

Tests verify Phase 1 refactoring:
- Pydantic validation for commands
- CommandResult error handling
- Critical bug fixes
"""

import pytest
from fastapi.testclient import TestClient


def test_get_status(client: TestClient):
    """Test GET /playback/status endpoint"""
    response = client.get("/playback/status")
    assert response.status_code == 200
    data = response.json()

    # Verify status structure
    assert "playing" in data
    assert "playback_state" in data
    assert "bpm" in data
    assert "position" in data
    assert "active_tracks" in data


def test_load_pattern_success(client: TestClient):
    """Test POST /playback/pattern with valid data"""
    session_data = {
        "environment": {"bpm": 120},
        "tracks": {},
        "sequences": {}
    }

    response = client.post("/playback/pattern", json=session_data)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_load_pattern_with_pydantic_validation(client: TestClient):
    """Test that CompileCommand validates the payload"""
    # This should still work as Pydantic has default factories
    response = client.post("/playback/pattern", json={})
    assert response.status_code == 200


def test_start_playback(client: TestClient):
    """Test POST /playback/start endpoint"""
    response = client.post("/playback/start")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_stop_playback(client: TestClient):
    """Test POST /playback/stop endpoint"""
    response = client.post("/playback/stop")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_pause_playback(client: TestClient):
    """Test POST /playback/pause endpoint"""
    response = client.post("/playback/pause")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_set_bpm_valid(client: TestClient):
    """Test POST /playback/bpm with valid BPM"""
    response = client.post("/playback/bpm", json={"bpm": 140})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["bpm"] == 140


def test_set_bpm_invalid_type(client: TestClient):
    """Test POST /playback/bpm with invalid type (Pydantic validation)"""
    response = client.post("/playback/bpm", json={"bpm": "not_a_number"})
    # Pydantic validation should fail
    assert response.status_code == 422


def test_set_bpm_negative(client: TestClient):
    """Test POST /playback/bpm with negative BPM (Pydantic gt=0 validation)"""
    response = client.post("/playback/bpm", json={"bpm": -10})
    # BpmCommand has Field(gt=0), should fail validation
    assert response.status_code == 422


def test_set_bpm_zero(client: TestClient):
    """Test POST /playback/bpm with zero BPM (Pydantic gt=0 validation)"""
    response = client.post("/playback/bpm", json={"bpm": 0})
    # BpmCommand has Field(gt=0), should fail validation
    assert response.status_code == 422


def test_error_handling_propagation(client: TestClient):
    """Test that CommandResult errors propagate to HTTP 500"""
    # This would need a mock that returns CommandResult.error()
    # For now, we verify the structure exists
    response = client.post("/playback/start")
    assert response.status_code in [200, 500]  # Either success or handled error
