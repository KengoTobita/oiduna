"""Tests for SessionLoader.

Tests cover:
- Destination loading from YAML
- OSC and MIDI destination registration
- Session loading with destination-based API
- Error handling for missing/invalid configurations
- Track registration from session messages
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Any

from oiduna.infrastructure.execution.session_loader import SessionLoader
from oiduna.infrastructure.execution.result import CommandResult
from oiduna.domain.models import OscDestinationConfig, MidiDestinationConfig


@pytest.fixture
def mock_destination_router():
    """Mock DestinationRouter."""
    router = Mock()
    router.register_destination = Mock()
    router.has_destination = Mock(return_value=True)
    router.get_registered_destinations = Mock(return_value=["superdirt"])
    return router


@pytest.fixture
def mock_message_scheduler():
    """Mock LoopScheduler."""
    scheduler = Mock()
    scheduler.load_messages = Mock()
    scheduler.message_count = 10
    scheduler.occupied_steps = [0, 64, 128]
    return scheduler


@pytest.fixture
def mock_state():
    """Mock RuntimeState."""
    state = Mock()
    state.set_bpm = Mock()
    state.register_track = Mock()
    return state


@pytest.fixture
def mock_callback():
    """Mock status update callback."""
    return Mock()


@pytest.fixture
def session_loader(mock_destination_router, mock_message_scheduler, mock_state, mock_callback):
    """Create SessionLoader with mocks."""
    return SessionLoader(
        destination_router=mock_destination_router,
        message_scheduler=mock_message_scheduler,
        state=mock_state,
        status_update_callback=mock_callback,
    )


class TestSessionLoaderInit:
    """Test SessionLoader initialization."""

    def test_init_sets_dependencies(self, session_loader, mock_destination_router):
        """Should store dependencies."""
        assert session_loader._destination_router is mock_destination_router
        assert session_loader.destinations_loaded is False


class TestLoadDestinations:
    """Test load_destinations method."""

    def test_load_destinations_file_not_found(self, session_loader, tmp_path):
        """Should return False when config file doesn't exist."""
        config_path = tmp_path / "nonexistent.yaml"

        result = session_loader.load_destinations(config_path)

        assert result is False
        assert session_loader.destinations_loaded is False

    @patch('oiduna.infrastructure.execution.session_loader.load_destinations_from_file')
    def test_load_destinations_with_osc(self, mock_load, session_loader, tmp_path, mock_destination_router):
        """Should register OSC destinations."""
        config_path = tmp_path / "destinations.yaml"
        config_path.touch()

        # Mock destination config
        osc_config = OscDestinationConfig(
            id="superdirt",
            type="osc",
            host="127.0.0.1",
            port=57120,
            address="/dirt/play",
            use_bundle=False
        )
        mock_load.return_value = {"superdirt": osc_config}

        result = session_loader.load_destinations(config_path)

        assert result is True
        assert session_loader.destinations_loaded is True
        mock_destination_router.register_destination.assert_called_once()

    @patch('oiduna.infrastructure.execution.session_loader.load_destinations_from_file')
    @patch('oiduna.infrastructure.execution.session_loader.MidiDestinationSender')
    def test_load_destinations_with_midi(self, mock_midi_sender, mock_load, session_loader, tmp_path, mock_destination_router):
        """Should register MIDI destinations."""
        config_path = tmp_path / "destinations.yaml"
        config_path.touch()

        # Mock destination config
        midi_config = MidiDestinationConfig(
            id="volca",
            type="midi",
            port_name="USB MIDI 1",
            default_channel=0
        )
        mock_load.return_value = {"volca": midi_config}

        # Mock MIDI sender creation
        mock_sender = Mock()
        mock_midi_sender.return_value = mock_sender

        result = session_loader.load_destinations(config_path)

        assert result is True
        assert session_loader.destinations_loaded is True
        mock_destination_router.register_destination.assert_called_once_with("volca", mock_sender)

    @patch('oiduna.infrastructure.execution.session_loader.load_destinations_from_file')
    @patch('oiduna.infrastructure.execution.session_loader.MidiDestinationSender')
    def test_load_destinations_midi_error_continues(self, mock_midi_sender, mock_load, session_loader, tmp_path):
        """Should skip MIDI destination on error and continue."""
        config_path = tmp_path / "destinations.yaml"
        config_path.touch()

        # Mock destination config
        midi_config = MidiDestinationConfig(
            id="volca",
            type="midi",
            port_name="Invalid Port",
            default_channel=0
        )
        mock_load.return_value = {"volca": midi_config}

        # Mock MIDI sender to raise exception
        mock_midi_sender.side_effect = Exception("Port not found")

        result = session_loader.load_destinations(config_path)

        # Should still succeed (True) even though MIDI dest failed
        assert result is True
        assert session_loader.destinations_loaded is True

    @patch('oiduna.infrastructure.execution.session_loader.load_destinations_from_file')
    def test_load_destinations_general_exception(self, mock_load, session_loader, tmp_path):
        """Should return False on general exception."""
        config_path = tmp_path / "destinations.yaml"
        config_path.touch()

        # Mock load_destinations_from_file to raise exception
        mock_load.side_effect = Exception("YAML parse error")

        result = session_loader.load_destinations(config_path)

        assert result is False
        assert session_loader.destinations_loaded is False


class TestLoadSession:
    """Test load_session method."""

    def test_load_session_destinations_not_loaded(self, session_loader):
        """Should fail if destinations not loaded."""
        payload = {"messages": [], "bpm": 120.0}

        result = session_loader.load_session(payload)

        assert result.success is False
        assert "Destination configuration not loaded" in result.message

    @patch('oiduna.infrastructure.execution.session_loader.LoopSchedule')
    def test_load_session_invalid_payload(self, mock_schedule, session_loader):
        """Should fail on invalid session payload."""
        session_loader._destinations_loaded = True

        # Mock LoopSchedule to raise exception
        mock_schedule.from_dict.side_effect = Exception("Invalid format")

        payload = {"invalid": "data"}
        result = session_loader.load_session(payload)

        assert result.success is False
        assert "Invalid session payload" in result.message

    @patch('oiduna.infrastructure.execution.session_loader.LoopSchedule')
    def test_load_session_missing_destination(self, mock_schedule, session_loader, mock_destination_router):
        """Should fail if session references unregistered destination."""
        session_loader._destinations_loaded = True

        # Mock LoopSchedule with unregistered destination
        mock_batch = Mock()
        mock_batch.destinations = ["superdirt", "unregistered"]
        mock_schedule.from_dict.return_value = mock_batch

        mock_destination_router.has_destination.side_effect = lambda d: d == "superdirt"
        mock_destination_router.get_registered_destinations.return_value = ["superdirt"]

        payload = {"messages": []}
        result = session_loader.load_session(payload)

        assert result.success is False
        assert "unregistered destinations" in result.message

    @patch('oiduna.infrastructure.execution.session_loader.LoopSchedule')
    def test_load_session_success(self, mock_schedule, session_loader, mock_message_scheduler, mock_state, mock_callback):
        """Should load session successfully."""
        session_loader._destinations_loaded = True

        # Mock LoopSchedule
        mock_message = Mock()
        mock_message.params = {"track_id": "kick", "s": "bd"}

        mock_batch = Mock()
        mock_batch.destinations = ["superdirt"]
        mock_batch.messages = [mock_message]
        mock_batch.bpm = 140.0
        mock_batch.pattern_length = 4.0
        mock_schedule.from_dict.return_value = mock_batch

        payload = {
            "messages": [
                {
                    "destination_id": "superdirt",
                    "offset": 0.0,
                    "step": 0,
                    "params": {"track_id": "kick", "s": "bd"}
                }
            ],
            "bpm": 140.0
        }

        result = session_loader.load_session(payload)

        assert result.success is True
        mock_message_scheduler.load_messages.assert_called_once_with(mock_batch)
        mock_state.set_bpm.assert_called_once_with(140.0)
        mock_state.register_track.assert_called_once_with("kick")
        mock_callback.assert_called_once()

    @patch('oiduna.infrastructure.execution.session_loader.LoopSchedule')
    def test_load_session_registers_multiple_tracks(self, mock_schedule, session_loader, mock_state):
        """Should register all track_ids from messages."""
        session_loader._destinations_loaded = True

        # Mock LoopSchedule with multiple tracks
        mock_msg1 = Mock()
        mock_msg1.params = {"track_id": "kick", "s": "bd"}

        mock_msg2 = Mock()
        mock_msg2.params = {"track_id": "hihat", "s": "hh"}

        mock_msg3 = Mock()
        mock_msg3.params = {"s": "sn"}  # No track_id

        mock_batch = Mock()
        mock_batch.destinations = ["superdirt"]
        mock_batch.messages = [mock_msg1, mock_msg2, mock_msg3]
        mock_batch.bpm = 120.0
        mock_batch.pattern_length = 4.0
        mock_schedule.from_dict.return_value = mock_batch

        payload = {"messages": []}
        result = session_loader.load_session(payload)

        assert result.success is True
        # Should register only tracks with track_id
        assert mock_state.register_track.call_count == 2
