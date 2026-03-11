"""
Oiduna Loop Engine - Execution Infrastructure

This module provides the execution infrastructure for Oiduna Loop Engine,
including step sequencing, MIDI clock generation, and note scheduling.

Main components:
- LoopEngine: Main loop engine orchestrating step processing and timing
- ClockGenerator: MIDI clock generation at 24 PPQ
- NoteScheduler: MIDI note scheduling and note-off timing
- CommandHandler: Playback command handling
- SessionLoader: Session and destination loading
- TimelineLoader: Timeline change application

State management:
- RuntimeState: Playback state, BPM, mute/solo filtering
- PlaybackState: Playback state enumeration
- Position: Playback position tracking
"""

from .clock_generator import ClockGenerator
from .command_handler import CommandHandler
from .commands import (
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
from .constants import (
    LOOP_STEPS,
    STEPS_PER_BEAT,
    STEPS_PER_BAR,
    CC_ALIASES,
    SPECIAL_MIDI_TARGETS,
    resolve_cc_target,
    is_special_midi_target,
)
from .loop_engine import LoopEngine
from .note_scheduler import NoteScheduler, PendingNoteOff
from .result import CommandResult
from .session_loader import SessionLoader
from .state.runtime_state import PlaybackState, Position, RuntimeState
from .timeline_loader import TimelineLoader

__all__ = [
    # Main engine
    "LoopEngine",
    # Components
    "ClockGenerator",
    "CommandHandler",
    "NoteScheduler",
    "SessionLoader",
    "TimelineLoader",
    # Commands
    "BpmCommand",
    "MidiPanicCommand",
    "MidiPortCommand",
    "MuteCommand",
    "PanicCommand",
    "PauseCommand",
    "PlayCommand",
    "SoloCommand",
    "StopCommand",
    # Constants
    "LOOP_STEPS",
    "STEPS_PER_BEAT",
    "STEPS_PER_BAR",
    "CC_ALIASES",
    "SPECIAL_MIDI_TARGETS",
    "resolve_cc_target",
    "is_special_midi_target",
    # Result
    "CommandResult",
    # State
    "PlaybackState",
    "Position",
    "RuntimeState",
    # Types
    "PendingNoteOff",
]
