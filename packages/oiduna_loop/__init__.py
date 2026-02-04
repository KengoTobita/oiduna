"""
Oiduna Loop Service

Real-time audio loop engine with OSC and MIDI output.
"""

__version__ = "0.2.0"

from .engine import LoopEngine
from .factory import create_loop_engine
from .protocols import CommandSource, MidiOutput, OscOutput, StateSink

__all__ = [
    "create_loop_engine",
    "LoopEngine",
    "MidiOutput",
    "OscOutput",
    "CommandSource",
    "StateSink",
]
