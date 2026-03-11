"""
Schedule domain models and compilation logic.

This package contains:
- ScheduleEntry, LoopSchedule: Compiled schedule data structures
- SessionCompiler: Converts Session to LoopSchedule
- Validators: OSC and MIDI message validation
"""

from .models import ScheduleEntry, LoopSchedule
from .compiler import SessionCompiler
from .validators import (
    OscValidator,
    OscValidationResult,
    MidiValidator,
    MidiValidationResult,
)

__all__ = [
    "ScheduleEntry",
    "LoopSchedule",
    "SessionCompiler",
    "OscValidator",
    "OscValidationResult",
    "MidiValidator",
    "MidiValidationResult",
]
