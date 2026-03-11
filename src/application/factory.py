"""
Oiduna Loop Factory

Factory functions for creating production LoopEngine instances.
Separates object creation from business logic (DI pattern).
"""

from __future__ import annotations

from typing import cast

from oiduna.infrastructure.ipc.protocols import (
    CommandConsumer,
    StateProducer,
)

from oiduna.infrastructure.execution import LoopEngine
from oiduna.infrastructure.ipc import InProcessStateProducer, NoopCommandConsumer
from oiduna.infrastructure.transport import MidiSender, OscSender


def create_loop_engine(
    osc_host: str = "127.0.0.1",
    osc_port: int = 57120,
    osc_address: str = "/dirt/play",
    midi_port: str | None = None,
    command_consumer: CommandConsumer | None = None,
    state_producer: StateProducer | None = None,
    before_send_hooks: list | None = None,
) -> LoopEngine:
    """
    Create a production LoopEngine with real I/O dependencies.

    Args:
        osc_host: OSC destination host
        osc_port: OSC destination port
        osc_address: OSC message address (default: "/dirt/play" for SuperDirt)
        midi_port: MIDI output port name (None for first available)
        command_consumer: CommandConsumer implementation (default: NoopCommandConsumer).
        state_producer: StateProducer implementation (default: InProcessStateProducer).
        before_send_hooks: Extension hooks for runtime message transformation

    Returns:
        Configured LoopEngine instance
    """
    osc = OscSender(osc_host, osc_port, osc_address)
    midi = MidiSender(midi_port)

    # Use defaults if not provided
    commands = command_consumer if command_consumer is not None else NoopCommandConsumer()
    publisher = state_producer if state_producer is not None else InProcessStateProducer()

    return LoopEngine(
        osc=osc,
        midi=midi,
        command_consumer=commands,
        state_producer=publisher,
        before_send_hooks=before_send_hooks,
    )
