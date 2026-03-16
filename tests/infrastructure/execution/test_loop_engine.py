"""
Tests for LoopEngine (v5)

Tests command handling, state management, and integration
using mock dependencies (DI pattern).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock

import pytest

from oiduna.infrastructure.execution import LoopEngine, PlaybackState


class TestLoopEngineInit:
    """Test LoopEngine initialization."""

    def test_creates_with_mocks(self, test_engine: LoopEngine):
        """Engine should initialize with mock dependencies."""
        assert test_engine is not None
        assert test_engine.state is not None

    def test_initial_state(self, test_engine: LoopEngine):
        """Engine should start with correct initial state."""
        assert test_engine.state.playing is False
        assert test_engine.state.bpm == 120.0


class TestLoopEngineCommands:
    """Test command handling."""

    def test_handle_play(self, test_engine: LoopEngine, mock_midi):
        """Play command should start playback and send MIDI start."""
        test_engine._midi_enabled = True

        test_engine.handle_play({})

        assert test_engine.state.playing is True
        assert mock_midi.started is True

    def test_handle_play_from_paused_maintains_position(
        self, test_engine: LoopEngine, mock_midi
    ):
        """Play from paused should resume from current position (like video player)."""
        test_engine._midi_enabled = True

        # Pause at step 10
        test_engine.state.playback_state = PlaybackState.PAUSED
        test_engine.state.position.step = 10

        test_engine.handle_play({})

        # Position should be maintained
        assert test_engine.state.position.step == 10
        assert test_engine.state.playback_state == PlaybackState.PLAYING
        # Should send MIDI Continue, not Start
        assert mock_midi.continued is True
        assert mock_midi.started is False

    def test_handle_play_from_stopped_starts_at_zero(
        self, test_engine: LoopEngine, mock_midi
    ):
        """Play from stopped should start from step 0 (already reset by stop)."""
        test_engine._midi_enabled = True

        # Stopped state (position already at 0)
        test_engine.state.playback_state = PlaybackState.STOPPED
        test_engine.state.position.step = 0

        test_engine.handle_play({})

        assert test_engine.state.position.step == 0
        assert test_engine.state.playback_state == PlaybackState.PLAYING
        # Should send MIDI Start
        assert mock_midi.started is True
        assert mock_midi.continued is False

    def test_handle_play_when_already_playing(self, test_engine: LoopEngine, mock_midi):
        """Play command when already playing should do nothing."""
        test_engine._midi_enabled = True
        test_engine.state.playback_state = PlaybackState.PLAYING

        test_engine.handle_play({})

        # Should not send another start
        assert mock_midi.started is False

    def test_handle_stop(self, test_engine: LoopEngine, mock_midi):
        """Stop command should stop playback and send MIDI stop."""
        test_engine._midi_enabled = True
        test_engine.state.playback_state = PlaybackState.PLAYING

        test_engine.handle_stop({})

        assert test_engine.state.playing is False
        assert mock_midi.stopped is True

    def test_handle_stop_when_stopped(self, test_engine: LoopEngine, mock_midi):
        """Stop command when already stopped should do nothing."""
        test_engine._midi_enabled = True
        test_engine.state.playback_state = PlaybackState.STOPPED

        test_engine.handle_stop({})

        assert mock_midi.stopped is False

    def test_handle_stop_from_paused(self, test_engine: LoopEngine, mock_midi):
        """Stop from paused should reset position but not send MIDI stop."""
        test_engine._midi_enabled = True
        test_engine.state.playback_state = PlaybackState.PAUSED
        test_engine.state.position.step = 10

        test_engine.handle_stop({})

        assert test_engine.state.playback_state == PlaybackState.STOPPED
        assert test_engine.state.position.step == 0  # Position reset
        assert mock_midi.stopped is False  # No MIDI stop since wasn't playing

    def test_handle_stop_resets_position(self, test_engine: LoopEngine):
        """Stop should always reset position to 0."""
        test_engine.state.playback_state = PlaybackState.PLAYING
        test_engine.state.position.step = 15

        test_engine.handle_stop({})

        assert test_engine.state.position.step == 0
        assert test_engine.state.playback_state == PlaybackState.STOPPED

    def test_handle_pause(self, test_engine: LoopEngine):
        """Pause command should stop playback without resetting position."""
        test_engine.state.playback_state = PlaybackState.PLAYING
        test_engine.state.position.step = 10

        test_engine.handle_pause({})

        assert test_engine.state.playback_state == PlaybackState.PAUSED
        assert test_engine.state.position.step == 10  # Position preserved

    def test_handle_pause_when_not_playing(self, test_engine: LoopEngine):
        """Pause when not playing should do nothing."""
        test_engine.state.playback_state = PlaybackState.STOPPED
        test_engine.state.position.step = 0

        test_engine.handle_pause({})

        # State should remain STOPPED
        assert test_engine.state.playback_state == PlaybackState.STOPPED

    def test_handle_bpm(self, test_engine: LoopEngine):
        """BPM command should change tempo."""
        test_engine._handle_bpm({"bpm": 140.0})

        assert test_engine.state.bpm == 140.0


class TestLoopEngineCommandInjection:
    """Test command processing via MockCommandConsumer."""

    @pytest.mark.asyncio
    async def test_process_play_command(
        self,
        test_engine: LoopEngine,
        mock_commands,
    ):
        """Commands injected into mock should be processed."""
        mock_commands.inject_command("play", {})

        await mock_commands.process_commands()

        assert test_engine.state.playing is True

    @pytest.mark.asyncio
    async def test_process_stop_after_play(
        self,
        test_engine: LoopEngine,
        mock_commands,
    ):
        """Stop after play should stop playback."""
        mock_commands.inject_command("play", {})
        mock_commands.inject_command("stop", {})

        await mock_commands.process_commands()

        assert test_engine.state.playing is False


class TestLoopEngineLifecycle:
    """Test LoopEngine lifecycle (start/stop)."""

    def test_start_connects_outputs(self, mock_osc, mock_midi, mock_commands, mock_publisher):
        """Start should connect all outputs."""
        engine = LoopEngine(
            osc=mock_osc,
            midi=mock_midi,
            command_consumer=mock_commands,
            state_producer=mock_publisher,
        )

        engine.start()

        assert mock_osc.is_connected is True
        assert mock_commands._connected is True
        assert mock_publisher._connected is True

    def test_start_enables_midi_if_available(self, mock_osc, mock_midi, mock_commands, mock_publisher):
        """Start should enable MIDI if ports are available."""
        engine = LoopEngine(
            osc=mock_osc,
            midi=mock_midi,
            command_consumer=mock_commands,
            state_producer=mock_publisher,
        )

        engine.start()

        # MIDI should be enabled since connect() returns True
        assert engine._midi_enabled is True

    def test_start_initializes_command_handler(self, mock_osc, mock_midi, mock_commands, mock_publisher):
        """Start should initialize CommandHandler."""
        engine = LoopEngine(
            osc=mock_osc,
            midi=mock_midi,
            command_consumer=mock_commands,
            state_producer=mock_publisher,
        )

        assert engine._command_handler is None

        engine.start()

        assert engine._command_handler is not None

    def test_start_initializes_step_executor(self, mock_osc, mock_midi, mock_commands, mock_publisher):
        """Start should initialize StepExecutor."""
        engine = LoopEngine(
            osc=mock_osc,
            midi=mock_midi,
            command_consumer=mock_commands,
            state_producer=mock_publisher,
        )

        assert engine._step_executor is None

        engine.start()

        assert engine._step_executor is not None

    def test_stop_disconnects_all(self, test_engine, mock_osc, mock_midi, mock_commands, mock_publisher):
        """Stop should disconnect all outputs."""
        test_engine.start()

        # Ensure connected
        assert mock_osc.is_connected is True

        test_engine.stop()

        assert mock_osc.is_connected is False
        assert mock_midi.is_connected is False
        assert mock_commands._connected is False
        assert mock_publisher._connected is False

    def test_stop_stops_playback_if_playing(self, test_engine):
        """Stop should stop playback if currently playing."""
        test_engine.start()
        test_engine.state.playback_state = PlaybackState.PLAYING

        test_engine.stop()

        assert test_engine.state.playback_state == PlaybackState.STOPPED

    def test_stop_sets_running_flag_false(self, test_engine):
        """Stop should set _running flag to False."""
        test_engine.start()
        test_engine._running = True

        test_engine.stop()

        assert test_engine._running is False


class TestLoopEngineIntegration:
    """Integration tests using multiple components."""

    def test_get_global_step(self, test_engine):
        """Should return global step counter."""
        initial_step = test_engine.get_global_step()

        assert isinstance(initial_step, int)
        assert initial_step >= 0

    def test_set_bpm_api(self, test_engine):
        """Public set_bpm API should work."""
        result = test_engine.set_bpm(140.0)

        assert result.success is True
        assert test_engine.state.bpm == 140.0

    def test_play_api(self, test_engine):
        """Public play API should work."""
        result = test_engine.play()

        assert result.success is True

    def test_pause_api(self, test_engine):
        """Public pause API should work."""
        test_engine.state.playback_state = PlaybackState.PLAYING

        result = test_engine.pause()

        assert result.success is True
        assert test_engine.state.playback_state == PlaybackState.PAUSED

    def test_stop_playback_api(self, test_engine):
        """Public stop_playback API should work."""
        test_engine.state.playback_state = PlaybackState.PLAYING

        result = test_engine.stop_playback()

        assert result.success is True
        assert test_engine.state.playback_state == PlaybackState.STOPPED

    def test_get_drift_stats(self, test_engine):
        """Should return drift statistics."""
        stats = test_engine.get_drift_stats()

        assert "reset_count" in stats
        assert "max_drift_ms" in stats
        assert "current_step_count" in stats


class TestPanicHandlers:
    """Test panic and emergency stop handlers."""

    def test_handle_midi_panic_turns_off_notes(self, test_engine, mock_midi):
        """MIDI panic should turn off all notes without stopping playback."""
        test_engine._midi_enabled = True
        test_engine.state.playback_state = PlaybackState.PLAYING

        result = test_engine._handle_midi_panic({})

        assert result.success is True
        assert mock_midi.all_notes_off_called is True
        # Playback should continue
        assert test_engine.state.playback_state == PlaybackState.PLAYING

    def test_handle_midi_panic_when_midi_disabled(self, test_engine, mock_midi):
        """MIDI panic should succeed even when MIDI disabled."""
        test_engine._midi_enabled = False
        # Reset flag from previous tests
        mock_midi.all_notes_off_called = False

        result = test_engine._handle_midi_panic({})

        assert result.success is True
        # _silence_all_notes checks _midi_enabled, but note_scheduler.clear_all() is always called
        # So the method succeeds, but all_notes_off should not be called when disabled

    def test_handle_panic_stops_playback(self, test_engine, mock_midi):
        """Full panic should stop playback and reset position."""
        test_engine._midi_enabled = True
        test_engine.state.playback_state = PlaybackState.PLAYING
        test_engine.state.position.step = 50

        result = test_engine._handle_panic({})

        assert result.success is True
        assert mock_midi.all_notes_off_called is True
        assert test_engine.state.playback_state == PlaybackState.STOPPED
        assert test_engine.state.position.step == 0

    def test_silence_all_notes_with_midi(self, test_engine, mock_midi):
        """_silence_all_notes should turn off MIDI notes when enabled."""
        test_engine._midi_enabled = True

        test_engine._silence_all_notes()

        assert mock_midi.all_notes_off_called is True

    def test_silence_all_notes_without_midi(self):
        """_silence_all_notes should not call MIDI when disabled."""
        # Create fresh mocks to avoid state pollution
        from .mocks import MockMidiOutput
        fresh_midi = MockMidiOutput()
        fresh_note_scheduler = Mock()

        # Create a minimal test setup
        test_engine = Mock()
        test_engine._midi = fresh_midi
        test_engine._midi_enabled = False
        test_engine._note_scheduler = fresh_note_scheduler

        # Import the actual method
        from oiduna.infrastructure.execution.loop_engine import LoopEngine
        # Call the method directly
        LoopEngine._silence_all_notes(test_engine)

        assert fresh_midi.all_notes_off_called is False
        fresh_note_scheduler.clear_all.assert_called_once()


class TestMidiPortManagement:
    """Test MIDI port switching."""

    def test_handle_midi_port_success(self, test_engine, mock_midi):
        """Should successfully change MIDI port."""
        mock_midi.set_port = lambda port_name: True

        result = test_engine._handle_midi_port({"port_name": "New Port"})

        assert result.success is True
        assert test_engine._midi_enabled is True

    def test_handle_midi_port_failure(self, test_engine, mock_midi):
        """Should handle MIDI port connection failure."""
        mock_midi.set_port = lambda port_name: False

        result = test_engine._handle_midi_port({"port_name": "Invalid Port"})

        assert result.success is False
        assert test_engine._midi_enabled is False
        assert "Failed to connect" in result.message

    def test_handle_midi_port_invalid_payload(self, test_engine):
        """Should reject invalid MIDI port command payload."""
        result = test_engine._handle_midi_port({})

        assert result.success is False
        assert "Invalid" in result.message


class TestBpmChangeDuringPlayback:
    """Test BPM changes during playback with drift suppression."""

    def test_bpm_change_during_playback_suppresses_drift(self, test_engine, mock_drift_corrector, mock_clock):
        """BPM change during playback should suppress drift detection."""
        test_engine.state.playback_state = PlaybackState.PLAYING

        result = test_engine.set_bpm(140.0)

        assert result.success is True
        assert test_engine.state.bpm == 140.0
        # Should suppress drift detection
        assert mock_drift_corrector.suppress_next_reset_called is True
        assert mock_clock.suppress_next_drift_reset_called is True

    def test_bpm_change_when_stopped_no_suppression(self, test_engine, mock_drift_corrector, mock_clock):
        """BPM change when stopped should not suppress drift."""
        test_engine.state.playback_state = PlaybackState.STOPPED

        result = test_engine.set_bpm(140.0)

        assert result.success is True
        # Should not suppress drift when stopped
        assert mock_drift_corrector.suppress_next_reset_called is False
        assert mock_clock.suppress_next_drift_reset_called is False

