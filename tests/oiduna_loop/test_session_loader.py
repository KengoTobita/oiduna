"""
Unit tests for SessionLoader.

Tests session loading and destination configuration loading.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from oiduna_loop.engine.session_loader import SessionLoader
from oiduna_loop.state import RuntimeState
from oiduna_scheduler.router import DestinationRouter
from oiduna_scheduler.scheduler import MessageScheduler
from oiduna_scheduler.scheduler_models import ScheduledMessage, ScheduledMessageBatch


class TestSessionLoader:
    """Test SessionLoader class."""

    @pytest.fixture
    def components(self):
        """Create mock components for SessionLoader."""
        destination_router = DestinationRouter()
        message_scheduler = MessageScheduler()
        state = RuntimeState()
        status_callback = MagicMock()

        return {
            "router": destination_router,
            "scheduler": message_scheduler,
            "state": state,
            "callback": status_callback,
        }

    @pytest.fixture
    def loader(self, components):
        """Create SessionLoader instance."""
        return SessionLoader(
            destination_router=components["router"],
            message_scheduler=components["scheduler"],
            state=components["state"],
            status_update_callback=components["callback"],
        )

    def test_initialization(self, loader):
        """SessionLoader should initialize with destinations not loaded."""
        assert loader.destinations_loaded is False

    def test_load_destinations_file_not_found(self, loader, tmp_path):
        """load_destinations should return False if file not found."""
        nonexistent_path = tmp_path / "nonexistent.yaml"

        result = loader.load_destinations(nonexistent_path)

        assert result is False
        assert loader.destinations_loaded is False

    def test_load_destinations_success(self, loader, tmp_path):
        """load_destinations should succeed with valid config."""
        # Create a simple destinations.yaml
        config_path = tmp_path / "destinations.yaml"
        config_path.write_text("""
destinations:
  superdirt:
    type: osc
    host: localhost
    port: 57120
    address: /dirt/play
    use_bundle: true
""")

        result = loader.load_destinations(config_path)

        assert result is True
        assert loader.destinations_loaded is True

    def test_load_session_destinations_not_loaded(self, loader):
        """load_session should fail if destinations not loaded."""
        payload = {
            "messages": [],
            "bpm": 120.0,
            "pattern_length": 4.0,
        }

        result = loader.load_session(payload)

        assert not result.success
        assert "destination configuration not loaded" in result.message.lower()

    def test_load_session_invalid_payload(self, loader):
        """load_session should fail with invalid payload."""
        # Enable destinations
        loader._destinations_loaded = True

        # Invalid payload (missing required fields)
        payload = {"invalid": "data"}

        result = loader.load_session(payload)

        assert not result.success
        assert "invalid session payload" in result.message.lower()

    def test_load_session_unregistered_destination(self, loader):
        """load_session should fail with unregistered destination."""
        # Enable destinations
        loader._destinations_loaded = True

        # Create session with unregistered destination
        payload = {
            "messages": [
                {
                    "destination_id": "nonexistent",
                    "cycle": 0.0,
                    "step": 0,
                    "params": {"s": "bd"},
                }
            ],
            "bpm": 120.0,
            "pattern_length": 4.0,
            "destinations": ["nonexistent"],
        }

        result = loader.load_session(payload)

        assert not result.success
        assert "unregistered destinations" in result.message.lower()
        assert "nonexistent" in result.message

    def test_load_session_success(self, loader, components):
        """load_session should succeed with valid payload and registered destination."""
        # Enable destinations and register one
        loader._destinations_loaded = True
        components["router"]._senders["superdirt"] = MagicMock()  # Mock sender

        # Create valid session
        payload = {
            "messages": [
                {
                    "destination_id": "superdirt",
                    "cycle": 0.0,
                    "step": 0,
                    "params": {"s": "bd", "track_id": "track1"},
                }
            ],
            "bpm": 140.0,
            "pattern_length": 4.0,
            "destinations": ["superdirt"],
        }

        result = loader.load_session(payload)

        # Should succeed
        assert result.success

        # BPM should be updated in state
        assert components["state"].bpm == 140.0

        # Status callback should be called
        components["callback"].assert_called_once()

        # Track should be registered (in known tracks)
        assert "track1" in components["state"]._known_track_ids

        # Messages should be loaded
        assert components["scheduler"].message_count == 1

    def test_load_session_multiple_destinations(self, loader, components):
        """load_session should work with multiple destinations."""
        # Enable destinations and register multiple
        loader._destinations_loaded = True
        components["router"]._senders["superdirt"] = MagicMock()
        components["router"]._senders["midi"] = MagicMock()

        # Create session with multiple destinations
        payload = {
            "messages": [
                {
                    "destination_id": "superdirt",
                    "cycle": 0.0,
                    "step": 0,
                    "params": {"s": "bd"},
                },
                {
                    "destination_id": "midi",
                    "cycle": 1.0,
                    "step": 64,
                    "params": {"note": 60},
                },
            ],
            "bpm": 120.0,
            "pattern_length": 4.0,
            "destinations": ["superdirt", "midi"],
        }

        result = loader.load_session(payload)

        assert result.success
        assert components["scheduler"].message_count == 2

    def test_load_session_partial_unregistered_fails(self, loader, components):
        """load_session should fail if any destination is unregistered."""
        # Enable destinations and register only one
        loader._destinations_loaded = True
        components["router"]._senders["superdirt"] = MagicMock()

        # Create session with mixed destinations
        payload = {
            "messages": [
                {
                    "destination_id": "superdirt",
                    "cycle": 0.0,
                    "step": 0,
                    "params": {"s": "bd"},
                },
                {
                    "destination_id": "midi",  # Not registered
                    "cycle": 1.0,
                    "step": 64,
                    "params": {"note": 60},
                },
            ],
            "bpm": 120.0,
            "pattern_length": 4.0,
            "destinations": ["superdirt", "midi"],
        }

        result = loader.load_session(payload)

        assert not result.success
        assert "midi" in result.message

    def test_load_session_registers_track_ids(self, loader, components):
        """load_session should register track_ids from message params."""
        # Enable destinations and register
        loader._destinations_loaded = True
        components["router"]._senders["superdirt"] = MagicMock()

        # Create session with track_ids
        payload = {
            "messages": [
                {
                    "destination_id": "superdirt",
                    "cycle": 0.0,
                    "step": 0,
                    "params": {"s": "bd", "track_id": "kick"},
                },
                {
                    "destination_id": "superdirt",
                    "cycle": 1.0,
                    "step": 64,
                    "params": {"s": "sn", "track_id": "snare"},
                },
            ],
            "bpm": 120.0,
            "pattern_length": 4.0,
            "destinations": ["superdirt"],
        }

        result = loader.load_session(payload)

        assert result.success
        # Both tracks should be registered (in known tracks)
        assert "kick" in components["state"]._known_track_ids
        assert "snare" in components["state"]._known_track_ids

    def test_load_session_empty_succeeds(self, loader):
        """load_session should succeed with empty message list."""
        # Enable destinations
        loader._destinations_loaded = True

        payload = {
            "messages": [],
            "bpm": 120.0,
            "pattern_length": 4.0,
            "destinations": [],
        }

        result = loader.load_session(payload)

        assert result.success
