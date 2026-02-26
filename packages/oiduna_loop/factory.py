"""
Oiduna Loop Factory

Factory functions for creating production LoopEngine instances.
Separates object creation from business logic (DI pattern).
"""

from __future__ import annotations

from typing import cast

from oiduna_core.protocols.ipc import CommandSource, StateSink

from .engine import LoopEngine
from .ipc import InProcessStateSink, NoopCommandSource
from .output import MidiSender, OscSender


def create_loop_engine(
    osc_host: str = "127.0.0.1",
    osc_port: int = 57120,
    osc_address: str = "/dirt/play",
    midi_port: str | None = None,
    command_source: CommandSource | None = None,
    state_sink: StateSink | None = None,
    before_send_hooks: list | None = None,
) -> LoopEngine:
    """
    Create a production LoopEngine with real I/O dependencies.

    Args:
        osc_host: OSC destination host
        osc_port: OSC destination port
        osc_address: OSC message address (default: "/dirt/play" for SuperDirt)
        midi_port: MIDI output port name (None for first available)
        command_source: CommandSource implementation (default: NoopCommandSource)
        state_sink: StateSink implementation (default: InProcessStateSink)
        before_send_hooks: Extension hooks for runtime message transformation

    Returns:
        Configured LoopEngine instance
    """
    osc = OscSender(osc_host, osc_port, osc_address)
    midi = MidiSender(midi_port)
    commands = cast(
        CommandSource,
        command_source if command_source is not None else NoopCommandSource()
    )
    publisher = cast(
        StateSink,
        state_sink if state_sink is not None else InProcessStateSink()
    )

    return LoopEngine(
        osc=osc,
        midi=midi,
        commands=commands,
        publisher=publisher,
        before_send_hooks=before_send_hooks,
    )
