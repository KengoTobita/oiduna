"""
End-to-end integration tests for the complete Oiduna flow.

Tests the full pipeline:
1. API Request → SessionContainer
2. SessionContainer → SessionCompiler
3. SessionCompiler → ScheduledMessageBatch
4. LoopEngine → SuperDirt/MIDI messages
5. SSE Events emission
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "packages"))

from oiduna_api.main import app
from oiduna_api.dependencies import get_container
from oiduna_session import SessionContainer, SessionCompiler
from oiduna_models import OscDestinationConfig
from oiduna_models import Event


@pytest.fixture
def client():
    """Create test client with real app."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_container():
    """Reset session container before each test."""
    container = get_container()
    container.reset()

    # Add test destination
    dest = OscDestinationConfig(
        id="superdirt",
        type="osc",
        host="127.0.0.1",
        port=57120,
        address="/dirt/play"
    )
    container.destinations.add(dest)

    yield

    container.reset()


class TestConfigEndpoint:
    """Test GET /config endpoint for structural information."""

    def test_config_basic_structure(self, client):
        """Test that /config returns basic structure without clients/destinations."""
        # Get config (no auth required)
        response = client.get("/config")
        assert response.status_code == 200

        data = response.json()

        # Check basic fields
        assert "environment" in data
        assert "loop_steps" in data
        assert "api_version" in data
        assert "clients" in data
        assert "destinations" in data

        # Check environment structure
        assert "bpm" in data["environment"]
        assert "position_update_interval" in data["environment"]

        # Check system constants
        assert data["loop_steps"] == 256
        assert data["api_version"] == "1.0"

    def test_config_with_clients_and_destinations(self, client):
        """Test that /config returns clients and destinations."""
        # Register a client
        response = client.post(
            "/clients/alice_001",
            json={
                "client_name": "Alice's MARS",
                "distribution": "mars"
            }
        )
        assert response.status_code == 201

        # Get config
        response = client.get("/config")
        assert response.status_code == 200

        data = response.json()

        # Check clients
        assert len(data["clients"]) == 1
        assert data["clients"][0]["client_id"] == "alice_001"
        assert data["clients"][0]["client_name"] == "Alice's MARS"
        assert data["clients"][0]["distribution"] == "mars"
        # Verify no token in response
        assert "token" not in data["clients"][0]

        # Check destinations (from fixture)
        assert len(data["destinations"]) == 1
        assert data["destinations"][0]["id"] == "superdirt"
        assert data["destinations"][0]["type"] == "osc"
        assert data["destinations"][0]["host"] == "127.0.0.1"
        assert data["destinations"][0]["port"] == 57120

    def test_config_multiple_clients(self, client):
        """Test that /config returns multiple clients."""
        # Register multiple clients
        client.post(
            "/clients/alice_001",
            json={"client_name": "Alice", "distribution": "mars"}
        )
        client.post(
            "/clients/bob_002",
            json={"client_name": "Bob", "distribution": "tidal"}
        )

        # Get config
        response = client.get("/config")
        assert response.status_code == 200

        data = response.json()
        assert len(data["clients"]) == 2

        # Verify both clients are present
        client_ids = [c["client_id"] for c in data["clients"]]
        assert "alice_001" in client_ids
        assert "bob_002" in client_ids

    def test_config_no_authentication_required(self, client):
        """Test that /config does not require authentication."""
        # Call without any auth headers
        response = client.get("/config")
        assert response.status_code == 200

        # Should return valid data
        data = response.json()
        assert "environment" in data
        assert "clients" in data
        assert "destinations" in data


class TestEndToEndFlow:
    """Test complete flow from API to message generation."""

    def test_full_flow_client_to_compiled_messages(self, client):
        """
        Test: API requests → SessionContainer → SessionCompiler → ScheduledMessageBatch

        Flow:
        1. Client registration (POST /clients/alice)
        2. Track creation (POST /tracks/kick)
        3. Pattern creation (POST /tracks/kick/patterns/main)
        4. Compile session → Verify generated messages
        """
        # Step 1: Register client
        response = client.post(
            "/clients/alice_001",
            json={
                "client_name": "Alice",
                "distribution": "mars"
            }
        )
        assert response.status_code == 201
        token = response.json()["token"]

        headers = {
            "X-Client-ID": "alice_001",
            "X-Client-Token": token
        }

        # Step 2: Create track
        response = client.post(
            "/tracks/kick",
            headers=headers,
            json={
                "track_name": "Kick Drum",
                "destination_id": "superdirt",
                "base_params": {"sound": "bd", "orbit": 0, "gain": 0.8}
            }
        )
        assert response.status_code == 201
        track_data = response.json()
        assert track_data["track_id"] == "kick"
        assert track_data["base_params"]["sound"] == "bd"

        # Step 3: Create pattern with events
        events = [
            {"step": 0, "cycle": 0.0, "params": {"n": 0}},
            {"step": 64, "cycle": 1.0, "params": {"n": 1, "gain": 0.9}},
            {"step": 128, "cycle": 2.0, "params": {"n": 2}},
        ]

        response = client.post(
            "/tracks/kick/patterns/main",
            headers=headers,
            json={
                "pattern_name": "Main Pattern",
                "active": True,
                "events": events
            }
        )
        assert response.status_code == 201
        pattern_data = response.json()
        assert pattern_data["pattern_id"] == "main"
        assert len(pattern_data["events"]) == 3

        # Step 4: Compile session and verify messages
        container = get_container()
        batch = SessionCompiler.compile(container.session)

        # Verify batch structure
        assert batch is not None
        assert batch.bpm == 120.0  # Default BPM
        assert len(batch.messages) == 3  # 3 events in pattern

        # Verify message content
        messages = sorted(batch.messages, key=lambda m: m.step)

        # First message (step 0)
        msg0 = messages[0]
        assert msg0.step == 0
        assert msg0.cycle == 0.0
        assert msg0.destination_id == "superdirt"
        assert msg0.params["sound"] == "bd"  # From base_params
        assert msg0.params["orbit"] == 0     # From base_params
        assert msg0.params["gain"] == 0.8    # From base_params
        assert msg0.params["n"] == 0         # From event

        # Second message (step 64)
        msg1 = messages[1]
        assert msg1.step == 64
        assert msg1.cycle == 1.0
        assert msg1.params["sound"] == "bd"
        assert msg1.params["n"] == 1
        assert msg1.params["gain"] == 0.9  # Event overrides base_params

        # Third message (step 128)
        msg2 = messages[2]
        assert msg2.step == 128
        assert msg2.cycle == 2.0
        assert msg2.params["n"] == 2

    def test_multiple_tracks_pattern_isolation(self, client):
        """
        Test multiple tracks with different patterns.
        Verify that each track's patterns are isolated and compiled correctly.
        """
        # Register client
        response = client.post(
            "/clients/alice_001",
            json={"client_name": "Alice"}
        )
        token = response.json()["token"]
        headers = {
            "X-Client-ID": "alice_001",
            "X-Client-Token": token
        }

        # Create track 1: kick
        client.post(
            "/tracks/kick",
            headers=headers,
            json={
                "track_name": "Kick",
                "destination_id": "superdirt",
                "base_params": {"sound": "bd", "orbit": 0}
            }
        )

        # Create track 2: snare
        client.post(
            "/tracks/snare",
            headers=headers,
            json={
                "track_name": "Snare",
                "destination_id": "superdirt",
                "base_params": {"sound": "sd", "orbit": 1}
            }
        )

        # Add pattern to kick (every beat)
        client.post(
            "/tracks/kick/patterns/main",
            headers=headers,
            json={
                "pattern_name": "Kick Pattern",
                "active": True,
                "events": [
                    {"step": 0, "cycle": 0.0, "params": {}},
                    {"step": 64, "cycle": 1.0, "params": {}},
                ]
            }
        )

        # Add pattern to snare (offbeat)
        client.post(
            "/tracks/snare/patterns/main",
            headers=headers,
            json={
                "pattern_name": "Snare Pattern",
                "active": True,
                "events": [
                    {"step": 32, "cycle": 0.5, "params": {}},
                    {"step": 96, "cycle": 1.5, "params": {}},
                ]
            }
        )

        # Compile and verify
        container = get_container()
        batch = SessionCompiler.compile(container.session)

        assert len(batch.messages) == 4  # 2 kick + 2 snare

        # Group messages by sound
        kick_messages = [m for m in batch.messages if m.params["sound"] == "bd"]
        snare_messages = [m for m in batch.messages if m.params["sound"] == "sd"]

        assert len(kick_messages) == 2
        assert len(snare_messages) == 2

        # Verify kick messages
        kick_steps = sorted([m.step for m in kick_messages])
        assert kick_steps == [0, 64]

        # Verify snare messages
        snare_steps = sorted([m.step for m in snare_messages])
        assert snare_steps == [32, 96]

        # Verify orbit isolation
        assert all(m.params["orbit"] == 0 for m in kick_messages)
        assert all(m.params["orbit"] == 1 for m in snare_messages)

    def test_inactive_pattern_exclusion(self, client):
        """
        Test that inactive patterns are excluded from compilation.
        """
        # Setup
        response = client.post("/clients/alice_001", json={"client_name": "Alice"})
        token = response.json()["token"]
        headers = {"X-Client-ID": "alice_001", "X-Client-Token": token}

        client.post(
            "/tracks/kick",
            headers=headers,
            json={"track_name": "Kick", "destination_id": "superdirt", "base_params": {"sound": "bd"}}
        )

        # Create active pattern
        client.post(
            "/tracks/kick/patterns/active",
            headers=headers,
            json={
                "pattern_name": "Active",
                "active": True,
                "events": [{"step": 0, "cycle": 0.0, "params": {}}]
            }
        )

        # Create inactive pattern
        client.post(
            "/tracks/kick/patterns/inactive",
            headers=headers,
            json={
                "pattern_name": "Inactive",
                "active": False,
                "events": [{"step": 64, "cycle": 1.0, "params": {}}]
            }
        )

        # Compile
        container = get_container()
        batch = SessionCompiler.compile(container.session)

        # Only active pattern's event should be compiled
        assert len(batch.messages) == 1
        assert batch.messages[0].step == 0

    def test_environment_bpm_propagation(self, client):
        """
        Test that environment BPM is correctly propagated to compiled batch.
        """
        # Setup
        response = client.post("/clients/alice_001", json={"client_name": "Alice"})
        token = response.json()["token"]
        headers = {"X-Client-ID": "alice_001", "X-Client-Token": token}

        # Update environment BPM
        response = client.patch(
            "/session/environment",
            headers=headers,
            json={"bpm": 140.0}
        )
        assert response.status_code == 200
        assert response.json()["bpm"] == 140.0

        # Create track and pattern
        client.post(
            "/tracks/kick",
            headers=headers,
            json={"track_name": "Kick", "destination_id": "superdirt", "base_params": {"sound": "bd"}}
        )
        client.post(
            "/tracks/kick/patterns/main",
            headers=headers,
            json={
                "pattern_name": "Main",
                "active": True,
                "events": [{"step": 0, "cycle": 0.0, "params": {}}]
            }
        )

        # Compile
        container = get_container()
        batch = SessionCompiler.compile(container.session)

        # Verify BPM
        assert batch.bpm == 140.0

    def test_param_merging_priority(self, client):
        """
        Test parameter merging: event params override base_params.
        """
        # Setup
        response = client.post("/clients/alice_001", json={"client_name": "Alice"})
        token = response.json()["token"]
        headers = {"X-Client-ID": "alice_001", "X-Client-Token": token}

        # Create track with base_params
        client.post(
            "/tracks/kick",
            headers=headers,
            json={
                "track_name": "Kick",
                "destination_id": "superdirt",
                "base_params": {
                    "sound": "bd",
                    "gain": 0.8,
                    "pan": 0.5,
                    "orbit": 0
                }
            }
        )

        # Create pattern with event that overrides some params
        client.post(
            "/tracks/kick/patterns/main",
            headers=headers,
            json={
                "pattern_name": "Main",
                "active": True,
                "events": [
                    {
                        "step": 0,
                        "cycle": 0.0,
                        "params": {
                            "gain": 1.0,  # Override
                            "n": 2        # New param
                        }
                    }
                ]
            }
        )

        # Compile
        container = get_container()
        batch = SessionCompiler.compile(container.session)

        # Verify parameter merging
        msg = batch.messages[0]
        assert msg.params["sound"] == "bd"   # From base_params
        assert msg.params["gain"] == 1.0     # Overridden by event
        assert msg.params["pan"] == 0.5      # From base_params
        assert msg.params["orbit"] == 0      # From base_params
        assert msg.params["n"] == 2          # From event


class TestSSEEventEmission:
    """Test that SSE events are properly emitted during operations."""

    def test_client_connected_event_emitted(self, client):
        """Test that client_connected event is emitted on client creation."""
        # We can't easily test async SSE in TestClient, but we can verify
        # the event sink was called by checking container's event_sink

        # This is more of a unit test, but belongs in integration context
        from unittest.mock import Mock

        container = get_container()
        mock_sink = Mock()
        container.event_sink = mock_sink
        container.clients.event_sink = mock_sink

        # Create client via API
        response = client.post(
            "/clients/test_001",
            json={"client_name": "Test"}
        )
        assert response.status_code == 201

        # Verify event was emitted
        assert mock_sink._push.called
        event = mock_sink._push.call_args[0][0]
        assert event["type"] == "client_connected"
        assert event["data"]["client_id"] == "test_001"

    def test_track_created_event_emitted(self, client):
        """Test that track_created event is emitted."""
        from unittest.mock import Mock

        # Setup
        response = client.post("/clients/alice_001", json={"client_name": "Alice"})
        token = response.json()["token"]
        headers = {"X-Client-ID": "alice_001", "X-Client-Token": token}

        # Attach mock sink
        container = get_container()
        mock_sink = Mock()
        container.event_sink = mock_sink
        container.tracks.event_sink = mock_sink

        # Create track
        response = client.post(
            "/tracks/kick",
            headers=headers,
            json={"track_name": "Kick", "destination_id": "superdirt"}
        )
        assert response.status_code == 201

        # Verify event
        assert mock_sink._push.called
        event = mock_sink._push.call_args[0][0]
        assert event["type"] == "track_created"
        assert event["data"]["track_id"] == "kick"


class TestMessageContentValidation:
    """Test that generated messages have correct structure and content."""

    def test_message_structure_compliance(self, client):
        """Test that generated ScheduledMessages comply with expected structure."""
        # Setup
        response = client.post("/clients/alice_001", json={"client_name": "Alice"})
        token = response.json()["token"]
        headers = {"X-Client-ID": "alice_001", "X-Client-Token": token}

        client.post(
            "/tracks/kick",
            headers=headers,
            json={"track_name": "Kick", "destination_id": "superdirt", "base_params": {"sound": "bd"}}
        )
        client.post(
            "/tracks/kick/patterns/main",
            headers=headers,
            json={
                "pattern_name": "Main",
                "active": True,
                "events": [{"step": 0, "cycle": 0.0, "params": {}}]
            }
        )

        # Compile
        container = get_container()
        batch = SessionCompiler.compile(container.session)
        msg = batch.messages[0]

        # Verify message structure
        assert hasattr(msg, "step")
        assert hasattr(msg, "cycle")
        assert hasattr(msg, "destination_id")
        assert hasattr(msg, "params")

        # Verify types
        assert isinstance(msg.step, int)
        assert isinstance(msg.cycle, float)
        assert isinstance(msg.destination_id, str)
        assert isinstance(msg.params, dict)

        # Verify required fields
        assert msg.step >= 0
        assert msg.step < 256  # LOOP_STEPS
        assert msg.cycle >= 0.0
        assert msg.destination_id == "superdirt"

    def test_message_serialization_for_loop_engine(self, client):
        """Test that messages can be serialized for LoopEngine consumption."""
        # Setup
        response = client.post("/clients/alice_001", json={"client_name": "Alice"})
        token = response.json()["token"]
        headers = {"X-Client-ID": "alice_001", "X-Client-Token": token}

        client.post(
            "/tracks/kick",
            headers=headers,
            json={
                "track_name": "Kick",
                "destination_id": "superdirt",
                "base_params": {"sound": "bd", "n": 0, "gain": 0.8}
            }
        )
        client.post(
            "/tracks/kick/patterns/main",
            headers=headers,
            json={
                "pattern_name": "Main",
                "active": True,
                "events": [{"step": 0, "cycle": 0.0, "params": {}}]
            }
        )

        # Compile
        container = get_container()
        batch = SessionCompiler.compile(container.session)

        # Serialize message to dict (what LoopEngine receives)
        msg_dict = batch.messages[0].to_dict()

        assert isinstance(msg_dict, dict)
        assert "step" in msg_dict
        assert "cycle" in msg_dict
        assert "destination_id" in msg_dict
        assert "params" in msg_dict

        # Verify params structure
        assert isinstance(msg_dict["params"], dict)
        assert "sound" in msg_dict["params"]
