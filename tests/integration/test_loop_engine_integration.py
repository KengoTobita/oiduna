"""
LoopEngine integration tests.

Tests the integration between SessionCompiler and LoopEngine:
- Message format compatibility
- Playback command execution
- Real-time compilation and updates
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "packages"))

from oiduna_api.main import app
from oiduna_api.dependencies import get_container
from oiduna_session import SessionCompiler
from oiduna_models import OscDestinationConfig


@pytest.fixture
def client():
    """Create test client with extension pipeline setup."""
    test_client = TestClient(app)

    # Mock extension pipeline (required by playback routes)
    mock_pipeline = Mock()
    mock_pipeline.extensions = []
    mock_pipeline.apply.side_effect = lambda x: x  # Pass-through
    app.state.extension_pipeline = mock_pipeline

    return test_client


@pytest.fixture(autouse=True)
def reset_container():
    """Reset container before each test."""
    container = get_container()
    container.reset()

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


class TestLoopEngineMessageFormat:
    """Test that compiled messages are compatible with LoopEngine."""

    def test_scheduled_message_batch_to_dict(self, client):
        """
        Test that ScheduledMessageBatch can be serialized to dict for LoopEngine.
        """
        # Setup session
        response = client.post("/clients/alice", json={"client_name": "Alice"})
        token = response.json()["token"]
        headers = {"X-Client-ID": "alice", "X-Client-Token": token}

        client.post(
            "/tracks/kick",
            headers=headers,
            json={
                "track_name": "Kick",
                "destination_id": "superdirt",
                "base_params": {"sound": "bd", "n": 0}
            }
        )

        client.post(
            "/tracks/kick/patterns/main",
            headers=headers,
            json={
                "pattern_name": "Main",
                "active": True,
                "events": [
                    {"step": 0, "cycle": 0.0, "params": {"gain": 0.9}},
                    {"step": 64, "cycle": 1.0, "params": {"gain": 0.7}}
                ]
            }
        )

        # Compile
        container = get_container()
        batch = SessionCompiler.compile(container.session)

        # Serialize to dict (LoopEngine format)
        batch_dict = {
            "messages": [msg.to_dict() for msg in batch.messages],
            "bpm": batch.bpm,
            "pattern_length": batch.pattern_length
        }

        # Verify structure
        assert "messages" in batch_dict
        assert "bpm" in batch_dict
        assert "pattern_length" in batch_dict

        assert isinstance(batch_dict["messages"], list)
        assert len(batch_dict["messages"]) == 2
        assert batch_dict["bpm"] == 120.0
        assert batch_dict["pattern_length"] == 4.0

        # Verify message format
        msg0 = batch_dict["messages"][0]
        assert msg0["step"] == 0
        assert msg0["cycle"] == 0.0
        assert msg0["destination_id"] == "superdirt"
        assert msg0["params"]["sound"] == "bd"
        assert msg0["params"]["n"] == 0
        assert msg0["params"]["gain"] == 0.9

    def test_empty_session_compilation(self, client):
        """Test that empty session produces valid empty batch."""
        container = get_container()
        batch = SessionCompiler.compile(container.session)

        assert batch is not None
        assert len(batch.messages) == 0
        assert batch.bpm == 120.0
        assert batch.pattern_length == 4.0


class TestPlaybackCommandIntegration:
    """Test playback API endpoints that interact with LoopEngine."""

    @pytest.fixture
    def mock_loop_service(self, monkeypatch):
        """Create a mock LoopService."""
        service = Mock()
        engine = Mock()

        # Mock CommandResult
        from oiduna_loop.result import CommandResult
        engine._handle_session.return_value = CommandResult.ok()
        engine._handle_compile.return_value = CommandResult.ok()
        engine._handle_play.return_value = CommandResult.ok()
        engine._handle_stop.return_value = CommandResult.ok()

        service.get_engine.return_value = engine

        # Replace global _loop_service with mock (same pattern as oiduna_api tests)
        from oiduna_api.services import loop_service
        monkeypatch.setattr(loop_service, "_loop_service", service)

        return service

    def test_sync_endpoint_sends_to_loop_engine(self, client, mock_loop_service):
        """
        Test that /playback/sync endpoint:
        1. Compiles session
        2. Sends ScheduledMessageBatch to LoopEngine
        """
        # Setup session
        response = client.post("/clients/alice", json={"client_name": "Alice"})
        token = response.json()["token"]
        headers = {"X-Client-ID": "alice", "X-Client-Token": token}

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

        # Call sync endpoint (compiles and loads session)
        response = client.post("/playback/sync", headers=headers)
        assert response.status_code == 200

        # Verify LoopEngine received the compiled session
        engine = mock_loop_service.get_engine()
        assert engine._handle_session.called

        # Get the payload sent to LoopEngine
        call_args = engine._handle_session.call_args[0][0]
        assert "messages" in call_args
        assert "bpm" in call_args

        # Verify message content
        messages = call_args["messages"]
        assert len(messages) == 1
        assert messages[0]["step"] == 0
        assert messages[0]["params"]["sound"] == "bd"

    def test_session_update_triggers_recompilation(self, client, mock_loop_service):
        """
        Test that updating session (adding pattern) and resyncing works.
        """
        # Setup
        response = client.post("/clients/alice", json={"client_name": "Alice"})
        token = response.json()["token"]
        headers = {"X-Client-ID": "alice", "X-Client-Token": token}

        client.post(
            "/tracks/kick",
            headers=headers,
            json={"track_name": "Kick", "destination_id": "superdirt", "base_params": {"sound": "bd"}}
        )

        # Sync empty track (version 0)
        sync_headers = {**headers, "X-Session-Version": "0"}
        response = client.post("/playback/sync", headers=sync_headers)
        assert response.status_code == 200

        engine = mock_loop_service.get_engine()
        first_call = engine._handle_session.call_args[0][0]
        assert len(first_call["messages"]) == 0  # No patterns yet

        # Add pattern
        client.post(
            "/tracks/kick/patterns/main",
            headers=headers,
            json={
                "pattern_name": "Main",
                "active": True,
                "events": [{"step": 0, "cycle": 0.0, "params": {}}]
            }
        )

        # Resync (version 1 after previous sync)
        sync_headers = {**headers, "X-Session-Version": "1"}
        response = client.post("/playback/sync", headers=sync_headers)
        assert response.status_code == 200

        # Verify updated messages
        second_call = engine._handle_session.call_args[0][0]
        assert len(second_call["messages"]) == 1  # Pattern added

    def test_sync_version_increment(self, client, mock_loop_service):
        """
        Test that successful sync increments session version.
        """
        # Setup
        response = client.post("/clients/alice", json={"client_name": "Alice"})
        token = response.json()["token"]
        headers = {"X-Client-ID": "alice", "X-Client-Token": token}

        client.post(
            "/tracks/kick",
            headers=headers,
            json={"track_name": "Kick", "destination_id": "superdirt", "base_params": {"sound": "bd"}}
        )

        # Get initial version
        from oiduna_api.dependencies import get_container
        container = get_container()
        initial_version = container.session.version
        assert initial_version == 0

        # First sync with version 0
        headers_with_version = {**headers, "X-Session-Version": "0"}
        response = client.post("/playback/sync", headers=headers_with_version)
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == 1
        assert container.session.version == 1
        assert container.session.last_modified_by == "alice"

        # Second sync with version 1
        headers_with_version = {**headers, "X-Session-Version": "1"}
        response = client.post("/playback/sync", headers=headers_with_version)
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == 2
        assert container.session.version == 2

    def test_sync_version_conflict(self, client, mock_loop_service):
        """
        Test that sync with outdated version returns 409 Conflict.
        """
        # Setup two clients
        response = client.post("/clients/alice", json={"client_name": "Alice"})
        alice_token = response.json()["token"]
        alice_headers = {"X-Client-ID": "alice", "X-Client-Token": alice_token}

        response = client.post("/clients/bob", json={"client_name": "Bob"})
        bob_token = response.json()["token"]
        bob_headers = {"X-Client-ID": "bob", "X-Client-Token": bob_token}

        # Setup track
        client.post(
            "/tracks/kick",
            headers=alice_headers,
            json={"track_name": "Kick", "destination_id": "superdirt", "base_params": {"sound": "bd"}}
        )

        # Alice syncs first (version 0 -> 1)
        alice_sync_headers = {**alice_headers, "X-Session-Version": "0"}
        response = client.post("/playback/sync", headers=alice_sync_headers)
        assert response.status_code == 200
        assert response.json()["version"] == 1

        # Bob tries to sync with old version 0 -> 409 Conflict
        bob_sync_headers = {**bob_headers, "X-Session-Version": "0"}
        response = client.post("/playback/sync", headers=bob_sync_headers)
        assert response.status_code == 409

        error = response.json()["detail"]
        assert error["error"] == "session_conflict"
        assert error["current_version"] == 1
        assert error["your_version"] == 0
        assert "alice" in error["message"]

        # Bob retries with correct version 1 -> success
        bob_sync_headers = {**bob_headers, "X-Session-Version": "1"}
        response = client.post("/playback/sync", headers=bob_sync_headers)
        assert response.status_code == 200
        assert response.json()["version"] == 2

    def test_sync_concurrent_operations_atomicity(self, client, mock_loop_service):
        """
        Test that operations within a sync are atomic (no interleaving).

        Scenario:
        - Client C makes changes: C1→C2→C3
        - Client D makes changes: D1→D2→D3
        - Both sync with same initial version
        - One succeeds (operations applied atomically)
        - Other gets 409 (prevented from interleaving)
        """
        # Setup two clients
        response = client.post("/clients/client_c", json={"client_name": "Client C"})
        c_token = response.json()["token"]
        c_headers = {"X-Client-ID": "client_c", "X-Client-Token": c_token}

        response = client.post("/clients/client_d", json={"client_name": "Client D"})
        d_token = response.json()["token"]
        d_headers = {"X-Client-ID": "client_d", "X-Client-Token": d_token}

        # Initial setup
        client.post(
            "/tracks/kick",
            headers=c_headers,
            json={"track_name": "Kick", "destination_id": "superdirt", "base_params": {"sound": "bd"}}
        )

        # Both clients remember version 0
        initial_version = 0

        # Client C syncs first (C1→C2→C3 applied atomically)
        c_sync_headers = {**c_headers, "X-Session-Version": str(initial_version)}
        response = client.post("/playback/sync", headers=c_sync_headers)
        assert response.status_code == 200
        assert response.json()["version"] == 1

        # Client D tries to sync with version 0 (D1→D2→D3)
        # This should fail because C already synced
        d_sync_headers = {**d_headers, "X-Session-Version": str(initial_version)}
        response = client.post("/playback/sync", headers=d_sync_headers)
        assert response.status_code == 409  # Conflict!

        # Verify C's operations were applied atomically (no interleaving with D)
        error = response.json()["detail"]
        assert error["current_version"] == 1
        assert error["your_version"] == 0
        assert "client_c" in error["message"]


class TestRealTimeUpdates:
    """Test real-time session updates and recompilation."""

    def test_pattern_activation_toggle(self, client):
        """Test toggling pattern active state and recompiling."""
        # Setup
        response = client.post("/clients/alice", json={"client_name": "Alice"})
        token = response.json()["token"]
        headers = {"X-Client-ID": "alice", "X-Client-Token": token}

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

        # Compile with active pattern
        container = get_container()
        batch1 = SessionCompiler.compile(container.session)
        assert len(batch1.messages) == 1

        # Deactivate pattern
        response = client.patch(
            "/tracks/kick/patterns/main",
            headers=headers,
            json={"active": False}
        )
        assert response.status_code == 200

        # Recompile - should have no messages
        batch2 = SessionCompiler.compile(container.session)
        assert len(batch2.messages) == 0

        # Reactivate
        client.patch(
            "/tracks/kick/patterns/main",
            headers=headers,
            json={"active": True}
        )

        # Recompile - should have messages again
        batch3 = SessionCompiler.compile(container.session)
        assert len(batch3.messages) == 1

    def test_base_params_update_propagation(self, client):
        """Test that updating track base_params affects compiled messages."""
        # Setup
        response = client.post("/clients/alice", json={"client_name": "Alice"})
        token = response.json()["token"]
        headers = {"X-Client-ID": "alice", "X-Client-Token": token}

        client.post(
            "/tracks/kick",
            headers=headers,
            json={
                "track_name": "Kick",
                "destination_id": "superdirt",
                "base_params": {"sound": "bd", "gain": 0.5}
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

        # Compile - initial gain
        container = get_container()
        batch1 = SessionCompiler.compile(container.session)
        assert batch1.messages[0].params["gain"] == 0.5

        # Update base_params
        client.patch(
            "/tracks/kick",
            headers=headers,
            json={"base_params": {"gain": 0.9}}
        )

        # Recompile - updated gain
        batch2 = SessionCompiler.compile(container.session)
        assert batch2.messages[0].params["gain"] == 0.9

    def test_bpm_update_propagation(self, client):
        """Test that updating environment BPM affects compiled batch."""
        # Setup
        response = client.post("/clients/alice", json={"client_name": "Alice"})
        token = response.json()["token"]
        headers = {"X-Client-ID": "alice", "X-Client-Token": token}

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

        # Initial BPM
        container = get_container()
        batch1 = SessionCompiler.compile(container.session)
        assert batch1.bpm == 120.0

        # Update BPM
        client.patch(
            "/session/environment",
            headers=headers,
            json={"bpm": 160.0}
        )

        # Recompile
        batch2 = SessionCompiler.compile(container.session)
        assert batch2.bpm == 160.0


class TestDestinationRouting:
    """Test that messages are routed to correct destinations."""

    def test_multiple_destinations(self, client):
        """Test routing messages to different destinations."""
        # Add MIDI destination
        container = get_container()
        from oiduna_models import MidiDestinationConfig

        midi_dest = MidiDestinationConfig(
            id="midi_synth",
            type="midi",
            port_name="TiMidity",
            channel=0
        )
        container.destinations.add(midi_dest)

        # Setup
        response = client.post("/clients/alice", json={"client_name": "Alice"})
        token = response.json()["token"]
        headers = {"X-Client-ID": "alice", "X-Client-Token": token}

        # Create OSC track
        client.post(
            "/tracks/kick_osc",
            headers=headers,
            json={
                "track_name": "Kick OSC",
                "destination_id": "superdirt",
                "base_params": {"sound": "bd"}
            }
        )

        # Create MIDI track
        client.post(
            "/tracks/synth_midi",
            headers=headers,
            json={
                "track_name": "Synth MIDI",
                "destination_id": "midi_synth",
                "base_params": {"note": 60}
            }
        )

        # Add patterns
        client.post(
            "/tracks/kick_osc/patterns/main",
            headers=headers,
            json={
                "pattern_name": "Main",
                "active": True,
                "events": [{"step": 0, "cycle": 0.0, "params": {}}]
            }
        )

        client.post(
            "/tracks/synth_midi/patterns/main",
            headers=headers,
            json={
                "pattern_name": "Main",
                "active": True,
                "events": [{"step": 0, "cycle": 0.0, "params": {}}]
            }
        )

        # Compile
        batch = SessionCompiler.compile(container.session)

        # Verify routing
        osc_messages = [m for m in batch.messages if m.destination_id == "superdirt"]
        midi_messages = [m for m in batch.messages if m.destination_id == "midi_synth"]

        assert len(osc_messages) == 1
        assert len(midi_messages) == 1

        assert osc_messages[0].params["sound"] == "bd"
        assert midi_messages[0].params["note"] == 60
