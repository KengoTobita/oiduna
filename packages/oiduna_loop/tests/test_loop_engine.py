"""
Tests for LoopEngine (v5)

Tests command handling, state management, and integration
using mock dependencies (DI pattern).
"""

from __future__ import annotations

from typing import Any

import pytest

from ..engine import LoopEngine
from ..state import PlaybackState


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
        assert len(test_engine.state.tracks) == 0


class TestLoopEngineCommands:
    """Test command handling."""

    def test_handle_compile(
        self, test_engine: LoopEngine, sample_session_data: dict[str, Any]
    ):
        """Compile command should load session data."""
        test_engine._handle_compile(sample_session_data)

        assert "kick" in test_engine.state.tracks
        assert "hihat" in test_engine.state.tracks
        assert test_engine.state.bpm == 120.0

    def test_handle_play(self, test_engine: LoopEngine, mock_midi):
        """Play command should start playback and send MIDI start."""
        test_engine._midi_enabled = True

        test_engine._handle_play({})

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

        test_engine._handle_play({})

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

        test_engine._handle_play({})

        assert test_engine.state.position.step == 0
        assert test_engine.state.playback_state == PlaybackState.PLAYING
        # Should send MIDI Start
        assert mock_midi.started is True
        assert mock_midi.continued is False

    def test_handle_play_when_already_playing(self, test_engine: LoopEngine, mock_midi):
        """Play command when already playing should do nothing."""
        test_engine._midi_enabled = True
        test_engine.state.playing = True

        test_engine._handle_play({})

        # Should not send another start
        assert mock_midi.started is False

    def test_handle_stop(self, test_engine: LoopEngine, mock_midi):
        """Stop command should stop playback and send MIDI stop."""
        test_engine._midi_enabled = True
        test_engine.state.playing = True

        test_engine._handle_stop({})

        assert test_engine.state.playing is False
        assert mock_midi.stopped is True

    def test_handle_stop_when_stopped(self, test_engine: LoopEngine, mock_midi):
        """Stop command when already stopped should do nothing."""
        test_engine._midi_enabled = True
        test_engine.state.playback_state = PlaybackState.STOPPED

        test_engine._handle_stop({})

        assert mock_midi.stopped is False

    def test_handle_stop_from_paused(self, test_engine: LoopEngine, mock_midi):
        """Stop from paused should reset position but not send MIDI stop."""
        test_engine._midi_enabled = True
        test_engine.state.playback_state = PlaybackState.PAUSED
        test_engine.state.position.step = 10

        test_engine._handle_stop({})

        assert test_engine.state.playback_state == PlaybackState.STOPPED
        assert test_engine.state.position.step == 0  # Position reset
        assert mock_midi.stopped is False  # No MIDI stop since wasn't playing

    def test_handle_stop_resets_position(self, test_engine: LoopEngine):
        """Stop should always reset position to 0."""
        test_engine.state.playback_state = PlaybackState.PLAYING
        test_engine.state.position.step = 15

        test_engine._handle_stop({})

        assert test_engine.state.position.step == 0
        assert test_engine.state.playback_state == PlaybackState.STOPPED

    def test_handle_pause(self, test_engine: LoopEngine):
        """Pause command should stop playback without resetting position."""
        test_engine.state.playback_state = PlaybackState.PLAYING
        test_engine.state.position.step = 10

        test_engine._handle_pause({})

        assert test_engine.state.playback_state == PlaybackState.PAUSED
        assert test_engine.state.position.step == 10  # Position preserved

    def test_handle_pause_when_not_playing(self, test_engine: LoopEngine):
        """Pause when not playing should do nothing."""
        test_engine.state.playback_state = PlaybackState.STOPPED
        test_engine.state.position.step = 0

        test_engine._handle_pause({})

        # State should remain STOPPED
        assert test_engine.state.playback_state == PlaybackState.STOPPED

    def test_handle_mute(
        self, test_engine: LoopEngine, sample_session_data: dict[str, Any]
    ):
        """Mute command should mute specified track."""
        test_engine._handle_compile(sample_session_data)

        test_engine._handle_mute({"track_id": "kick", "mute": True})

        # v5: mute is in track.meta.mute
        assert test_engine.state.tracks["kick"].meta.mute is True

    def test_handle_unmute(
        self, test_engine: LoopEngine, sample_session_data: dict[str, Any]
    ):
        """Mute command with mute=False should unmute track."""
        test_engine._handle_compile(sample_session_data)
        # First mute, then unmute
        test_engine._handle_mute({"track_id": "kick", "mute": True})

        test_engine._handle_mute({"track_id": "kick", "mute": False})

        assert test_engine.state.tracks["kick"].meta.mute is False

    def test_handle_solo(
        self, test_engine: LoopEngine, sample_session_data: dict[str, Any]
    ):
        """Solo command should solo specified track."""
        test_engine._handle_compile(sample_session_data)

        test_engine._handle_solo({"track_id": "kick", "solo": True})

        # v5: solo is in track.meta.solo
        assert test_engine.state.tracks["kick"].meta.solo is True

    def test_handle_bpm(self, test_engine: LoopEngine):
        """BPM command should change tempo."""
        test_engine._handle_bpm({"bpm": 140.0})

        assert test_engine.state.bpm == 140.0


class TestLoopEngineCommandInjection:
    """Test command processing via MockCommandSource."""

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
    async def test_process_multiple_commands(
        self,
        test_engine: LoopEngine,
        mock_commands,
        sample_session_data: dict[str, Any],
    ):
        """Multiple commands should be processed in order."""
        mock_commands.inject_command("compile", sample_session_data)
        mock_commands.inject_command("play", {})

        await mock_commands.process_commands()

        assert "kick" in test_engine.state.tracks
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


class TestLoopEngineIntegration:
    """Integration tests using multiple components."""

    def test_full_workflow(
        self,
        test_engine: LoopEngine,
        mock_midi,
        sample_session_data: dict[str, Any],
    ):
        """Test complete workflow: compile, play, stop."""
        test_engine._midi_enabled = True

        # Compile session
        test_engine._handle_compile(sample_session_data)
        assert "kick" in test_engine.state.tracks

        # Start playback
        test_engine._handle_play({})
        assert test_engine.state.playing is True
        assert mock_midi.started is True

        # Stop playback
        test_engine._handle_stop({})
        assert test_engine.state.playing is False
        assert mock_midi.stopped is True

    def test_solo_affects_active_tracks(
        self,
        test_engine: LoopEngine,
        sample_session_data: dict[str, Any],
    ):
        """Solo should affect which tracks are active."""
        test_engine._handle_compile(sample_session_data)

        # Initially both tracks are active
        active = test_engine.state.get_active_tracks()
        assert len(active) == 2

        # Solo kick
        test_engine._handle_solo({"track_id": "kick", "solo": True})

        # Only kick should be active
        active = test_engine.state.get_active_tracks()
        assert len(active) == 1
        assert "kick" in active

    def test_mute_affects_active_tracks(
        self,
        test_engine: LoopEngine,
        sample_session_data: dict[str, Any],
    ):
        """Mute should affect which tracks are active."""
        test_engine._handle_compile(sample_session_data)

        # Mute kick
        test_engine._handle_mute({"track_id": "kick", "mute": True})

        # Only hihat should be active
        active = test_engine.state.get_active_tracks()
        assert len(active) == 1
        assert "hihat" in active
