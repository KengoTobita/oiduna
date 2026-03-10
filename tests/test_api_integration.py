"""
Integration tests for new API endpoints.

Tests the full flow: Client registration → Track creation → Pattern creation → Sync
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent.parent / "packages"))

from oiduna_api.main import app
from oiduna_api.dependencies import get_container
from oiduna_session import SessionContainer
from oiduna_models import OscDestinationConfig


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_session_manager():
    """Reset session container before each test."""
    container = get_container()
    container.reset()

    # Add a test destination
    dest = OscDestinationConfig(
        id="superdirt",
        type="osc",
        host="127.0.0.1",
        port=57120,
        address="/dirt/play"
    )
    container.destinations.add(dest)

    yield

    # Cleanup
    container.reset()


class TestClientAuth:
    """Test client authentication endpoints."""

    def test_create_client(self, client):
        """Test creating a client."""
        response = client.post(
            "/clients/alice_001",
            json={
                "client_name": "Alice",
                "distribution": "mars",
                "metadata": {}
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["client_id"] == "alice_001"
        assert data["client_name"] == "Alice"
        assert "token" in data
        assert len(data["token"]) == 36

    def test_create_duplicate_client(self, client):
        """Test creating duplicate client fails."""
        client.post(
            "/clients/alice_001",
            json={"client_name": "Alice"}
        )
        response = client.post(
            "/clients/alice_001",
            json={"client_name": "Bob"}
        )
        assert response.status_code == 409

    def test_list_clients(self, client):
        """Test listing clients."""
        # Create two clients
        client.post("/clients/alice_001", json={"client_name": "Alice"})
        client.post("/clients/bob_001", json={"client_name": "Bob"})

        # List clients
        response = client.get("/clients")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert {c["client_id"] for c in data} == {"alice_001", "bob_001"}
        # Tokens should not be in list response
        assert "token" not in data[0]

    def test_get_client(self, client):
        """Test getting a client."""
        client.post("/clients/alice_001", json={"client_name": "Alice"})

        response = client.get("/clients/alice_001")
        assert response.status_code == 200
        data = response.json()
        assert data["client_id"] == "alice_001"
        assert "token" not in data


class TestTrackManagement:
    """Test track CRUD endpoints."""

    def test_create_track(self, client, auth_headers):
        """Test creating a track with server-generated ID."""
        response = client.post(
            "/tracks",
            headers=auth_headers,
            json={
                "track_name": "kick",
                "destination_id": "superdirt",
                "base_params": {"sound": "bd", "orbit": 0}
            }
        )
        assert response.status_code == 201
        data = response.json()

        # Validate server-generated ID format (4-char hex, session-scoped)
        track_id = data["track_id"]
        assert len(track_id) == 4
        assert all(c in "0123456789abcdef" for c in track_id)

        assert data["track_name"] == "kick"
        assert data["base_params"]["sound"] == "bd"

    def test_create_track_invalid_destination(self, client, auth_headers):
        """Test creating track with invalid destination fails."""
        response = client.post(
            "/tracks",
            headers=auth_headers,
            json={
                "track_name": "kick",
                "destination_id": "invalid",
                "base_params": {}
            }
        )
        assert response.status_code == 400

    def test_create_track_invalid_destination_format_with_space(self, client, auth_headers):
        """Test creating track with space in destination_id fails with 422."""
        response = client.post(
            "/tracks",
            headers=auth_headers,
            json={
                "track_name": "kick",
                "destination_id": "super dirt",
                "base_params": {}
            }
        )
        assert response.status_code == 422
        # Check that validation error message contains helpful info
        detail = response.json()["detail"]
        assert any("alphanumeric" in str(err) for err in detail)

    def test_create_track_invalid_destination_format_with_special_char(self, client, auth_headers):
        """Test creating track with special char in destination_id fails with 422."""
        response = client.post(
            "/tracks",
            headers=auth_headers,
            json={
                "track_name": "kick",
                "destination_id": "dest!",
                "base_params": {}
            }
        )
        assert response.status_code == 422
        detail = response.json()["detail"]
        assert any("alphanumeric" in str(err) for err in detail)

    def test_create_track_valid_destination_format_succeeds(self, client, auth_headers):
        """Test creating track with valid destination_id format succeeds."""
        response = client.post(
            "/tracks",
            headers=auth_headers,
            json={
                "track_name": "kick",
                "destination_id": "superdirt",
                "base_params": {}
            }
        )
        assert response.status_code == 201

        # Validate server-generated ID (4-char hex, session-scoped)
        track_id = response.json()["track_id"]
        assert len(track_id) == 4
        assert all(c in "0123456789abcdef" for c in track_id)

    def test_create_track_valid_format_nonexistent_destination_returns_400(self, client, auth_headers):
        """Test valid format but nonexistent destination returns 400 (not 422)."""
        response = client.post(
            "/tracks",
            headers=auth_headers,
            json={
                "track_name": "snare",
                "destination_id": "osc-synth",  # Valid format, but doesn't exist
                "base_params": {}
            }
        )
        assert response.status_code == 400
        assert "does not exist" in response.json()["detail"]

    def test_list_tracks(self, client, auth_headers):
        """Test listing tracks."""
        # Create two tracks
        client.post(
            "/tracks",
            headers=auth_headers,
            json={"track_name": "kick", "destination_id": "superdirt"}
        )
        client.post(
            "/tracks",
            headers=auth_headers,
            json={"track_name": "snare", "destination_id": "superdirt"}
        )

        # List tracks
        response = client.get("/tracks", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_update_track(self, client, auth_headers):
        """Test updating track base params."""
        # Create track and extract ID
        create_response = client.post(
            "/tracks",
            headers=auth_headers,
            json={
                "track_name": "kick",
                "destination_id": "superdirt",
                "base_params": {"sound": "bd"}
            }
        )
        track_id = create_response.json()["track_id"]

        # Update base params
        response = client.patch(
            f"/tracks/{track_id}",
            headers=auth_headers,
            json={"base_params": {"gain": 0.8}}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["base_params"]["sound"] == "bd"  # Original param preserved
        assert data["base_params"]["gain"] == 0.8  # New param added

    def test_delete_track(self, client, auth_headers):
        """Test deleting a track."""
        # Create track and extract ID
        create_response = client.post(
            "/tracks",
            headers=auth_headers,
            json={"track_name": "kick", "destination_id": "superdirt"}
        )
        track_id = create_response.json()["track_id"]

        # Delete track
        response = client.delete(f"/tracks/{track_id}", headers=auth_headers)
        assert response.status_code == 204

        # Verify archived
        response = client.get(f"/tracks/{track_id}", headers=auth_headers)
        assert response.status_code == 404


class TestPatternManagement:
    """Test pattern CRUD endpoints."""

    def test_create_pattern(self, client, auth_headers_with_track):
        """Test creating a pattern with server-generated ID."""
        # Get the track ID from the fixture
        track_id = auth_headers_with_track["_track_id"]
        
        response = client.post(
            f"/tracks/{track_id}/patterns",
            headers=auth_headers_with_track,
            json={
                "pattern_name": "main",
                "active": True,
                "events": [
                    {"step": 0, "cycle": 0.0, "params": {}},
                    {"step": 64, "cycle": 1.0, "params": {"gain": 0.9}}
                ]
            }
        )
        assert response.status_code == 201
        data = response.json()

        # Validate server-generated pattern ID format (4-char hex, session-scoped)
        pattern_id = data["pattern_id"]
        assert len(pattern_id) == 4
        assert all(c in "0123456789abcdef" for c in pattern_id)

        assert data["pattern_name"] == "main"
        assert data["track_id"] == track_id  # Pattern has track_id field
        assert data["archived"] is False  # Pattern has archived field
        assert len(data["events"]) == 2

    def test_update_pattern(self, client, auth_headers_with_track):
        """Test updating a pattern."""
        # Get the track ID from the fixture
        track_id = auth_headers_with_track["_track_id"]
        
        # Create pattern and extract ID
        create_response = client.post(
            f"/tracks/{track_id}/patterns",
            headers=auth_headers_with_track,
            json={"pattern_name": "main", "active": True, "events": []}
        )
        pattern_id = create_response.json()["pattern_id"]

        # Update pattern
        response = client.patch(
            f"/tracks/{track_id}/patterns/{pattern_id}",
            headers=auth_headers_with_track,
            json={"active": False}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["active"] is False

    def test_delete_pattern(self, client, auth_headers_with_track):
        """Test deleting a pattern."""
        # Get the track ID from the fixture
        track_id = auth_headers_with_track["_track_id"]
        
        # Create pattern and extract ID
        create_response = client.post(
            f"/tracks/{track_id}/patterns",
            headers=auth_headers_with_track,
            json={"pattern_name": "main", "active": True, "events": []}
        )
        pattern_id = create_response.json()["pattern_id"]

        # Delete pattern
        response = client.delete(
            f"/tracks/{track_id}/patterns/{pattern_id}",
            headers=auth_headers_with_track
        )
        assert response.status_code == 204


class TestSessionManagement:
    """Test session state endpoints."""

    def test_get_session_state(self, client, auth_headers):
        """Test getting session state."""
        response = client.get("/session/state", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "environment" in data
        assert "destinations" in data
        assert "clients" in data
        assert "tracks" in data

    def test_update_environment(self, client, auth_headers):
        """Test updating environment."""
        response = client.patch(
            "/session/environment",
            headers=auth_headers,
            json={"bpm": 140.0, "metadata": {"key": "Am"}}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["bpm"] == 140.0
        assert data["metadata"]["key"] == "Am"


class TestAdminEndpoints:
    """Test admin endpoints."""

    @pytest.fixture
    def admin_headers(self):
        """Return admin auth headers."""
        return {"X-Admin-Password": "change_me_in_production"}

    def test_list_destinations(self, client, admin_headers):
        """Test listing destinations."""
        response = client.get("/admin/destinations", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "destinations" in data

    def test_reset_session(self, client, admin_headers):
        """Test resetting session."""
        response = client.post("/admin/session/reset", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "previous_counts" in data

    def test_admin_auth_required(self, client):
        """Test admin endpoints require password."""
        response = client.get(
            "/admin/destinations",
            headers={"X-Admin-Password": "wrong"}
        )
        assert response.status_code == 403
