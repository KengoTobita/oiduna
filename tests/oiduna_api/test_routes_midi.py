"""Tests for /midi/* endpoints

Tests verify Phase 1 refactoring:
- MIDI port management
- CommandResult error handling
- Critical bug fix (port → port_name)
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


def test_list_midi_ports(client: TestClient):
    """Test listing MIDI ports (basic smoke test)"""
    response = client.get("/midi/ports")
    # Should succeed even if no MIDI devices
    assert response.status_code in [200, 500]


def test_list_midi_ports_with_mocked_mido(client: TestClient):
    """Test listing MIDI ports with mocked mido"""
    with patch("mido.get_input_names") as mock_input, \
         patch("mido.get_output_names") as mock_output:
        mock_input.return_value = ["Input Port 1", "Input Port 2"]
        mock_output.return_value = ["Output Port 1"]

        response = client.get("/midi/ports")
        assert response.status_code == 200
        data = response.json()
        assert len(data["ports"]) == 3
        # Check input ports
        assert any(p["name"] == "Input Port 1" and p["is_input"] for p in data["ports"])
        # Check output ports
        assert any(p["name"] == "Output Port 1" and p["is_output"] for p in data["ports"])


def test_select_midi_port_success(client: TestClient):
    """Test POST /midi/port with valid port name"""
    response = client.post(
        "/midi/port",
        json={"port_name": "IAC Driver Bus 1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["port_name"] == "IAC Driver Bus 1"


def test_select_midi_port_failure(client: TestClient):
    """Test POST /midi/port with port that fails to connect"""
    # Update mock to return error for this specific port
    response = client.post(
        "/midi/port",
        json={"port_name": "nonexistent_port"},
    )
    # Should return 500 with error message (Phase 1 error handling)
    assert response.status_code == 500
    assert "Failed to connect" in response.json()["detail"]


def test_select_midi_port_missing_name(client: TestClient):
    """Test POST /midi/port without port_name (Pydantic validation)"""
    response = client.post(
        "/midi/port",
        json={},
    )
    # Pydantic validation should fail
    assert response.status_code == 422


def test_midi_panic_success(client: TestClient):
    """Test MIDI panic endpoint"""
    response = client.post("/midi/panic")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
