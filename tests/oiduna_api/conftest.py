"""Test fixtures for oiduna_api tests"""

import sys
from pathlib import Path

# Add packages to sys.path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir / "packages" / "oiduna_api"))
sys.path.insert(0, str(root_dir / "packages" / "oiduna_loop"))
sys.path.insert(0, str(root_dir / "packages" / "oiduna_core"))
sys.path.insert(0, str(root_dir / "packages" / "osc_protocol"))

import asyncio
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, MagicMock, AsyncMock

from oiduna_api.main import app


@pytest.fixture
def mock_loop_service():
    """Create a mock LoopService for testing"""
    service = Mock()

    # Mock engine with state
    engine = Mock()

    # Mock position with step and beat attributes
    position = Mock()
    position.step = 0
    position.beat = 0
    position.bar = 0
    engine.state.position = position

    engine.state.to_status_dict.return_value = {
        "playing": False,
        "playback_state": "stopped",
        "bpm": 120,
        "position": {"step": 0, "beat": 0, "bar": 0},
        "active_tracks": [],
        "has_pending": False,
        "scenes": [],
        "current_scene": None,
    }

    # Mock get_effective for tracks
    effective = Mock()
    effective.tracks = {}
    effective.sequences = {}
    engine.state.get_effective.return_value = effective

    # Mock CommandResult returns
    from oiduna_loop.result import CommandResult

    # MIDI panic always succeeds
    engine._handle_midi_panic.return_value = CommandResult.ok()

    # MIDI port selection - return error for nonexistent_port
    def mock_midi_port(payload):
        port_name = payload.get("port_name")
        if port_name == "nonexistent_port":
            return CommandResult.error(f"Failed to connect to MIDI port: {port_name}")
        return CommandResult.ok()

    engine._handle_midi_port.side_effect = mock_midi_port

    # Mute/Solo return error for nonexistent tracks
    def mock_mute(payload):
        track_id = payload.get("track_id")
        if track_id == "nonexistent":
            return CommandResult.error(f"Track '{track_id}' not found")
        return CommandResult.ok()

    def mock_solo(payload):
        track_id = payload.get("track_id")
        if track_id == "nonexistent":
            return CommandResult.error(f"Track '{track_id}' not found")
        return CommandResult.ok()

    engine._handle_mute.side_effect = mock_mute
    engine._handle_solo.side_effect = mock_solo

    # Scene command - return error for nonexistent scenes
    def mock_scene(payload):
        scene_name = payload.get("name")
        if scene_name == "nonexistent_scene":
            return CommandResult.error(f"Scene '{scene_name}' not found")
        return CommandResult.ok()

    engine._handle_scene.side_effect = mock_scene

    # Playback commands always succeed in tests
    engine._handle_compile.return_value = CommandResult.ok()
    engine._handle_play.return_value = CommandResult.ok()
    engine._handle_stop.return_value = CommandResult.ok()
    engine._handle_pause.return_value = CommandResult.ok()
    engine._handle_bpm.return_value = CommandResult.ok()

    service.get_engine.return_value = engine

    # Mock state sink with async queue
    state_sink = Mock()
    queue = AsyncMock()
    # By default, make queue.get() raise TimeoutError (heartbeat behavior)
    queue.get = AsyncMock(side_effect=asyncio.TimeoutError)
    state_sink.queue = queue
    service.get_state_sink.return_value = state_sink

    return service


@pytest.fixture
def client(mock_loop_service, monkeypatch):
    """Create a test client with mocked LoopService"""
    from oiduna_api.services import loop_service

    # Replace global _loop_service with mock
    monkeypatch.setattr(loop_service, "_loop_service", mock_loop_service)

    return TestClient(app)


@pytest.fixture
def minimal_session():
    """Minimal valid session data"""
    return {
        "environment": {"bpm": 120, "scale": "minor"},
        "tracks": [],
        "scenes": [],
    }


@pytest.fixture
def simple_session():
    """Simple session with one track"""
    return {
        "environment": {"bpm": 120, "scale": "minor"},
        "tracks": [
            {
                "id": "bd",
                "sound": "bd",
                "orbit": 0,
                "gain": 1.0,
                "pan": 0.5,
                "muted": False,
                "solo": False,
                "length": 1,
                "sequence": [{"pitch": "0", "length": 1}],
            }
        ],
        "scenes": [],
    }
