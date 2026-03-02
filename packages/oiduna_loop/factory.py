"""
Oiduna Loop Factory

Factory functions for creating production LoopEngine instances.
Separates object creation from business logic (DI pattern).
"""

from __future__ import annotations

from typing import cast

from .ipc.protocols import (
    CommandConsumer,
    CommandSource,  # Legacy, for backward compatibility
    StateProducer,
    StateSink,  # Legacy, for backward compatibility
)

from .engine import LoopEngine
from .ipc import InProcessStateSink, NoopCommandSource
from .output import MidiSender, OscSender


def create_loop_engine(
    osc_host: str = "127.0.0.1",
    osc_port: int = 57120,
    osc_address: str = "/dirt/play",
    midi_port: str | None = None,
    command_consumer: CommandConsumer | CommandSource | None = None,
    state_producer: StateProducer | StateSink | None = None,
    # Legacy parameter names (deprecated, kept for backward compatibility)
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
        command_consumer: CommandConsumer implementation (default: NoopCommandSource).
            Accepts CommandConsumer (new) or CommandSource (legacy).
        state_producer: StateProducer implementation (default: InProcessStateSink).
            Accepts StateProducer (new) or StateSink (legacy).
        command_source: DEPRECATED. Use command_consumer instead.
        state_sink: DEPRECATED. Use state_producer instead.
        before_send_hooks: Extension hooks for runtime message transformation

    Returns:
        Configured LoopEngine instance
    """
    osc = OscSender(osc_host, osc_port, osc_address)
    midi = MidiSender(midi_port)

    # Handle legacy parameter names
    final_command_consumer = command_consumer or command_source
    final_state_producer = state_producer or state_sink

    commands = cast(
        CommandConsumer,
        final_command_consumer if final_command_consumer is not None else NoopCommandSource()
    )
    publisher = cast(
        StateProducer,
        final_state_producer if final_state_producer is not None else InProcessStateSink()
    )

    return LoopEngine(
        osc=osc,
        midi=midi,
        command_consumer=commands,
        state_producer=publisher,
        before_send_hooks=before_send_hooks,
    )
