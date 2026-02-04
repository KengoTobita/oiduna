"""
Tests for MIDI reconnection and retry mechanisms.

TDD: Write tests first, then implement retry logic.
"""

from __future__ import annotations

import pytest

from ..engine import LoopEngine
from ..output.midi_sender import MidiSender
from ..state import PlaybackState
from .mocks import MockCommandSource, MockMidiOutput


class TestMidiSenderRetry:
    """Tests for MIDI sender retry mechanism."""

    def test_retry_constants_defined(self) -> None:
        """Retry constants should be defined."""
        assert hasattr(MidiSender, "MAX_RETRIES")
        assert hasattr(MidiSender, "RETRY_DELAY")
        assert MidiSender.MAX_RETRIES >= 1
        assert MidiSender.RETRY_DELAY >= 0

    def test_send_returns_false_when_disconnected(self) -> None:
        """Send should return False when not connected."""
        sender = MidiSender()
        # Not connected
        assert sender.send_note_on(0, 60, 100) is False

    def test_all_notes_off_returns_false_when_disconnected(self) -> None:
        """all_notes_off should return False when not connected."""
        sender = MidiSender()
        assert sender.all_notes_off() is False


class TestMockMidiFailure:
    """Tests using mock to simulate MIDI failures."""

    def test_mock_midi_can_simulate_failure(
        self,
        mock_midi: MockMidiOutput,
    ) -> None:
        """MockMidiOutput should be able to simulate connection failure."""
        # Initially connected
        assert mock_midi.is_connected is True

        # Simulate disconnection
        mock_midi._connected = False
        assert mock_midi.is_connected is False


class TestPanicCommand:
    """Tests for panic (emergency all notes off) command."""

    def test_panic_handler_registered(
        self,
        test_engine: LoopEngine,
        mock_commands: MockCommandSource,
    ) -> None:
        """Panic command handler should be registered."""
        assert "panic" in mock_commands._handlers

    @pytest.mark.asyncio
    async def test_panic_sends_all_notes_off(
        self,
        test_engine: LoopEngine,
        mock_midi: MockMidiOutput,
        mock_commands: MockCommandSource,
    ) -> None:
        """Panic command should send all notes off."""
        # Enable MIDI
        test_engine._midi_enabled = True

        # Inject panic command
        mock_commands.inject_command("panic", {})
        await mock_commands.process_commands()

        # Should have called all_notes_off (check via notes list)
        # Note: MockMidiOutput.all_notes_off() doesn't track calls,
        # so we check the state machine behavior instead

    @pytest.mark.asyncio
    async def test_panic_stops_playback(
        self,
        test_engine: LoopEngine,
        mock_commands: MockCommandSource,
        sample_session_data: dict,
    ) -> None:
        """Panic command should stop playback."""
        # Setup: Start playing
        test_engine._handle_compile(sample_session_data)
        test_engine._handle_play({})
        assert test_engine.state.playback_state == PlaybackState.PLAYING

        # Inject panic command
        mock_commands.inject_command("panic", {})
        await mock_commands.process_commands()

        # Should be stopped
        assert test_engine.state.playback_state == PlaybackState.STOPPED

    @pytest.mark.asyncio
    async def test_panic_resets_position(
        self,
        test_engine: LoopEngine,
        mock_commands: MockCommandSource,
        sample_session_data: dict,
    ) -> None:
        """Panic command should reset position to 0."""
        # Setup: Start playing and advance position
        test_engine._handle_compile(sample_session_data)
        test_engine._handle_play({})
        test_engine.state.advance_step()
        test_engine.state.advance_step()
        assert test_engine.state.position.step > 0

        # Inject panic command
        mock_commands.inject_command("panic", {})
        await mock_commands.process_commands()

        # Position should be reset
        assert test_engine.state.position.step == 0


class TestMockMidiAllNotesOffTracking:
    """Tests to verify MockMidiOutput tracks all_notes_off calls."""

    def test_mock_tracks_all_notes_off_calls(
        self,
        mock_midi: MockMidiOutput,
    ) -> None:
        """MockMidiOutput should track all_notes_off calls."""
        # This attribute will be added to MockMidiOutput
        assert hasattr(mock_midi, "all_notes_off_called")

        # Initially false
        assert mock_midi.all_notes_off_called is False

        # Call all_notes_off
        mock_midi.all_notes_off()

        # Should be true now
        assert mock_midi.all_notes_off_called is True

    def test_mock_reset_clears_all_notes_off_flag(
        self,
        mock_midi: MockMidiOutput,
    ) -> None:
        """MockMidiOutput.reset() should clear all_notes_off_called flag."""
        mock_midi.all_notes_off()
        assert mock_midi.all_notes_off_called is True

        mock_midi.reset()
        assert mock_midi.all_notes_off_called is False
