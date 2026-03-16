"""Tests for CommandHandler.

Tests cover:
- Play/Stop/Pause commands
- BPM command
- Mute/Solo commands  
- Panic commands
- Validation errors
- State transitions
"""

import pytest
from unittest.mock import Mock, MagicMock

from oiduna.infrastructure.execution.command_handler import CommandHandler
from oiduna.infrastructure.execution.state.runtime_state import PlaybackState


@pytest.fixture
def mock_state():
    """Mock RuntimeState."""
    state = Mock()
    state.playback_state = PlaybackState.STOPPED
    state.bpm = 120.0
    state.reset_position = Mock()
    state.set_bpm = Mock()
    state.set_track_mute = Mock(return_value=True)
    state.set_track_solo = Mock(return_value=True)
    return state


@pytest.fixture
def mock_clock_generator():
    """Mock ClockGenerator."""
    mock = Mock()
    mock.set_bpm = Mock()
    return mock


@pytest.fixture
def mock_note_scheduler():
    """Mock NoteScheduler."""
    mock = Mock()
    mock.clear = Mock()
    mock.clear_all = Mock()
    return mock


@pytest.fixture
def mock_publisher():
    """Mock StateProducer."""
    mock = Mock()
    mock.send_tracks = Mock()
    return mock


@pytest.fixture
def handler(mock_state, mock_clock_generator, mock_note_scheduler, mock_publisher):
    """Create CommandHandler with mocks."""
    return CommandHandler(
        state=mock_state,
        clock_generator=mock_clock_generator,
        note_scheduler=mock_note_scheduler,
        publisher=mock_publisher,
        midi_enabled=True
    )


class TestPlayCommand:
    """Test handle_play command."""

    def test_play_from_stopped(self, handler, mock_state):
        """Test play from stopped state."""
        mock_state.playback_state = PlaybackState.STOPPED

        result = handler.handle_play({})

        assert result.success is True
        assert mock_state.playback_state == PlaybackState.PLAYING

    def test_play_from_paused(self, handler, mock_state):
        """Test play from paused state (resume)."""
        mock_state.playback_state = PlaybackState.PAUSED

        result = handler.handle_play({})

        assert result.success is True
        assert mock_state.playback_state == PlaybackState.PLAYING

    def test_play_when_already_playing(self, handler, mock_state):
        """Test play when already playing does nothing."""
        mock_state.playback_state = PlaybackState.PLAYING

        result = handler.handle_play({})

        assert result.success is True
        assert "Already playing" in result.message


class TestStopCommand:
    """Test handle_stop command."""

    def test_stop_from_playing(self, handler, mock_state):
        """Test stop from playing state."""
        mock_state.playback_state = PlaybackState.PLAYING

        result = handler.handle_stop({})

        assert result.success is True
        assert mock_state.playback_state == PlaybackState.STOPPED
        mock_state.reset_position.assert_called_once()

    def test_stop_from_paused(self, handler, mock_state):
        """Test stop from paused state."""
        mock_state.playback_state = PlaybackState.PAUSED

        result = handler.handle_stop({})

        assert result.success is True
        assert mock_state.playback_state == PlaybackState.STOPPED
        mock_state.reset_position.assert_called_once()

    def test_stop_when_already_stopped(self, handler, mock_state):
        """Test stop when already stopped."""
        mock_state.playback_state = PlaybackState.STOPPED

        result = handler.handle_stop({})

        assert result.success is True
        assert "Already stopped" in result.message


class TestPauseCommand:
    """Test handle_pause command."""

    def test_pause_from_playing(self, handler, mock_state):
        """Test pause from playing state."""
        mock_state.playback_state = PlaybackState.PLAYING

        result = handler.handle_pause({})

        assert result.success is True
        assert mock_state.playback_state == PlaybackState.PAUSED

    def test_pause_when_stopped(self, handler, mock_state):
        """Test pause when stopped does nothing."""
        mock_state.playback_state = PlaybackState.STOPPED

        result = handler.handle_pause({})

        assert result.success is True
        assert "Not playing" in result.message


class TestBpmCommand:
    """Test handle_bpm command."""

    def test_set_valid_bpm(self, handler, mock_state):
        """Test setting valid BPM."""
        result = handler.handle_bpm({"bpm": 140.0})

        assert result.success is True
        mock_state.set_bpm.assert_called_once_with(140.0)

    def test_set_bpm_minimum(self, handler, mock_state):
        """Test setting minimum BPM (1.0)."""
        result = handler.handle_bpm({"bpm": 1.0})

        assert result.success is True
        mock_state.set_bpm.assert_called_once_with(1.0)

    def test_set_bpm_maximum(self, handler, mock_state):
        """Test setting maximum BPM (999.0)."""
        result = handler.handle_bpm({"bpm": 999.0})

        assert result.success is True
        mock_state.set_bpm.assert_called_once_with(999.0)

    def test_set_invalid_bpm_zero(self, handler):
        """Test setting BPM to zero fails."""
        result = handler.handle_bpm({"bpm": 0.0})

        assert result.success is False
        assert "Invalid" in result.message

    def test_set_invalid_bpm_negative(self, handler):
        """Test setting negative BPM fails."""
        result = handler.handle_bpm({"bpm": -10.0})

        assert result.success is False
        assert "Invalid" in result.message


class TestMuteCommand:
    """Test handle_mute command."""

    def test_mute_track(self, handler, mock_state):
        """Test muting a track."""
        mock_state.set_track_mute.return_value = True

        result = handler.handle_mute({"track_id": "0001", "mute": True})

        assert result.success is True
        mock_state.set_track_mute.assert_called_once_with("0001", True)

    def test_unmute_track(self, handler, mock_state):
        """Test unmuting a track."""
        mock_state.set_track_mute.return_value = True

        result = handler.handle_mute({"track_id": "0001", "mute": False})

        assert result.success is True
        mock_state.set_track_mute.assert_called_once_with("0001", False)

    def test_mute_track_not_found(self, handler, mock_state):
        """Test mute with non-existent track."""
        mock_state.set_track_mute.return_value = False

        result = handler.handle_mute({"track_id": "9999", "mute": True})

        assert result.success is False
        assert "not found" in result.message

    def test_mute_missing_track_id(self, handler):
        """Test mute without track_id fails."""
        result = handler.handle_mute({"mute": True})

        assert result.success is False


class TestSoloCommand:
    """Test handle_solo command."""

    def test_solo_track(self, handler, mock_state):
        """Test soloing a track."""
        mock_state.set_track_solo.return_value = True

        result = handler.handle_solo({"track_id": "0001", "solo": True})

        assert result.success is True
        mock_state.set_track_solo.assert_called_once_with("0001", True)

    def test_unsolo_track(self, handler, mock_state):
        """Test unsoloing a track."""
        mock_state.set_track_solo.return_value = True

        result = handler.handle_solo({"track_id": "0001", "solo": False})

        assert result.success is True
        mock_state.set_track_solo.assert_called_once_with("0001", False)

    def test_solo_track_not_found(self, handler, mock_state):
        """Test solo with non-existent track."""
        mock_state.set_track_solo.return_value = False

        result = handler.handle_solo({"track_id": "9999", "solo": True})

        assert result.success is False
        assert "not found" in result.message

    def test_solo_missing_track_id(self, handler):
        """Test solo without track_id fails."""
        result = handler.handle_solo({"solo": True})

        assert result.success is False


class TestPanicCommand:
    """Test handle_panic command."""

    def test_panic_clears_notes(self, handler, mock_note_scheduler):
        """Test panic clears all notes."""
        result = handler.handle_panic({})

        assert result.success is True
        mock_note_scheduler.clear_all.assert_called_once()

    def test_panic_does_not_stop_playback(self, handler, mock_state):
        """Test panic does NOT change playback state."""
        mock_state.playback_state = PlaybackState.PLAYING

        result = handler.handle_panic({})

        assert result.success is True
        # Panic does not stop playback, only clears notes
        assert mock_state.playback_state == PlaybackState.PLAYING
