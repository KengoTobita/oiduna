"""
Command handler for LoopEngine playback control.

Handles playback commands (play, stop, pause, bpm, mute, solo, panic).
Extracted from LoopEngine to follow Single Responsibility Principle.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError

from ..commands import (
    BpmCommand,
    MidiPanicCommand,
    MidiPortCommand,
    MuteCommand,
    PanicCommand,
    PauseCommand,
    PlayCommand,
    SoloCommand,
    StopCommand,
)
from ..protocols import StateSink
from ..result import CommandResult
from ..state import PlaybackState, RuntimeState
from .clock_generator import ClockGenerator
from .note_scheduler import NoteScheduler

logger = logging.getLogger(__name__)


class CommandHandler:
    """
    Handles playback commands (play, stop, pause, bpm, mute, solo).

    Responsibilities:
    - Validate command payloads
    - Update RuntimeState
    - Send MIDI clock messages
    - Clear note scheduler on stop
    - Schedule status updates

    Depends on:
    - RuntimeState: playback state, BPM, mute/solo
    - ClockGenerator: MIDI clock messages
    - NoteScheduler: note-off cleanup
    - StateSink: status/tracks updates
    """

    def __init__(
        self,
        state: RuntimeState,
        clock_generator: ClockGenerator,
        note_scheduler: NoteScheduler,
        publisher: StateSink,
        midi_enabled: bool = False,
    ):
        """
        Initialize CommandHandler.

        Args:
            state: Runtime state (playback, BPM, mute/solo)
            clock_generator: MIDI clock generator
            note_scheduler: Note scheduler for cleanup
            publisher: State publisher for updates
            midi_enabled: Whether MIDI is enabled
        """
        self.state = state
        self._clock_generator = clock_generator
        self._note_scheduler = note_scheduler
        self._publisher = publisher
        self._midi_enabled = midi_enabled

    def handle_play(self, payload: dict[str, Any]) -> CommandResult:
        """
        Start or resume playback (like video player play button).

        Public API for playback control - can be called directly from routes.
        Note: MIDI operations are handled by LoopEngine wrapper.
        """
        try:
            # Validate payload with Pydantic
            cmd = PlayCommand(**payload)
        except ValidationError as e:
            return CommandResult.error(f"Invalid play command: {e}")

        current_state = self.state.playback_state

        if current_state == PlaybackState.PLAYING:
            # Already playing, do nothing
            return CommandResult.ok("Already playing")

        # Update playback state
        self.state.playback_state = PlaybackState.PLAYING

        if current_state == PlaybackState.STOPPED:
            logger.info("Playback started from beginning")
        elif current_state == PlaybackState.PAUSED:
            logger.info(f"Playback resumed from step {self.state.position.step}")

        return CommandResult.ok()

    def handle_stop(self, payload: dict[str, Any]) -> CommandResult:
        """
        Stop playback and reset to beginning (like video player stop button).

        Public API for playback control - can be called directly from routes.
        Note: MIDI operations and note cleanup are handled by LoopEngine wrapper.
        """
        try:
            # Validate payload with Pydantic
            cmd = StopCommand(**payload)
        except ValidationError as e:
            return CommandResult.error(f"Invalid stop command: {e}")

        if self.state.playback_state == PlaybackState.STOPPED:
            # Already stopped, do nothing
            return CommandResult.ok("Already stopped")

        # Reset position and set state
        self.state.reset_position()
        self.state.playback_state = PlaybackState.STOPPED

        logger.info("Playback stopped, position reset")

        return CommandResult.ok()

    def handle_pause(self, payload: dict[str, Any]) -> CommandResult:
        """
        Pause playback, maintaining position (like video player pause button).

        Public API for playback control - can be called directly from routes.
        Note: MIDI operations and note cleanup are handled by LoopEngine wrapper.
        """
        try:
            # Validate payload with Pydantic
            cmd = PauseCommand(**payload)
        except ValidationError as e:
            return CommandResult.error(f"Invalid pause command: {e}")

        if self.state.playback_state != PlaybackState.PLAYING:
            # Not playing, do nothing
            return CommandResult.ok("Not playing")

        # Set paused state (position is maintained)
        self.state.playback_state = PlaybackState.PAUSED
        logger.info(f"Playback paused at step {self.state.position.step}")

        return CommandResult.ok()

    def handle_mute(self, payload: dict[str, Any]) -> CommandResult:
        """Mute/unmute a track"""
        try:
            cmd = MuteCommand(**payload)
        except ValidationError as e:
            return CommandResult.error(f"Invalid mute command: {e}")

        if self.state.set_track_mute(cmd.track_id, cmd.mute):
            logger.debug(f"Track '{cmd.track_id}' mute={cmd.mute}")
            return CommandResult.ok()
        else:
            return CommandResult.error(f"Track '{cmd.track_id}' not found")

    def handle_solo(self, payload: dict[str, Any]) -> CommandResult:
        """Solo/unsolo a track"""
        try:
            cmd = SoloCommand(**payload)
        except ValidationError as e:
            return CommandResult.error(f"Invalid solo command: {e}")

        if self.state.set_track_solo(cmd.track_id, cmd.solo):
            logger.debug(f"Track '{cmd.track_id}' solo={cmd.solo}")
            return CommandResult.ok()
        else:
            return CommandResult.error(f"Track '{cmd.track_id}' not found")

    def handle_bpm(self, payload: dict[str, Any]) -> CommandResult:
        """Change BPM"""
        try:
            cmd = BpmCommand(**payload)
        except ValidationError as e:
            return CommandResult.error(f"Invalid BPM command: {e}")

        old_bpm = self.state.bpm
        self.state.set_bpm(cmd.bpm)
        logger.info(f"BPM changed: {old_bpm} → {cmd.bpm}")

        return CommandResult.ok()

    def handle_midi_port(self, payload: dict[str, Any]) -> CommandResult:
        """Change MIDI port (not implemented in CommandHandler)"""
        try:
            cmd = MidiPortCommand(**payload)
        except ValidationError as e:
            return CommandResult.error(f"Invalid MIDI port command: {e}")

        # MIDI port change requires access to MidiOutput
        # This should remain in LoopEngine
        return CommandResult.error("MIDI port change must be handled by LoopEngine")

    def handle_midi_panic(self, payload: dict[str, Any]) -> CommandResult:
        """MIDI panic (not implemented in CommandHandler)"""
        try:
            cmd = MidiPanicCommand(**payload)
        except ValidationError as e:
            return CommandResult.error(f"Invalid MIDI panic command: {e}")

        # MIDI panic requires access to MidiOutput
        # This should remain in LoopEngine
        return CommandResult.error("MIDI panic must be handled by LoopEngine")

    def handle_panic(self, payload: dict[str, Any]) -> CommandResult:
        """Panic: stop all notes"""
        try:
            cmd = PanicCommand(**payload)
        except ValidationError as e:
            return CommandResult.error(f"Invalid panic command: {e}")

        self._note_scheduler.clear_all()
        logger.info("Panic: all notes cleared")

        return CommandResult.ok()
