"""
Test Doubles for oiduna_loop

Mock implementations of Protocol interfaces for unit testing.
These allow testing LoopEngine and related components without
real I/O dependencies (MIDI hardware, OSC network, ZeroMQ).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from oiduna_core.models.output import OscEvent


@dataclass
class MockMidiOutput:
    """
    Test double for MidiOutput protocol.

    Records all MIDI operations for test assertions.
    """

    notes: list[tuple[str, int, int, int]] = field(default_factory=list)
    cc_messages: list[tuple[int, int, int]] = field(default_factory=list)  # (channel, cc, value)
    pitch_bends: list[tuple[int, int]] = field(default_factory=list)  # (channel, value)
    aftertouches: list[tuple[int, int]] = field(default_factory=list)  # (channel, value)
    clocks: int = 0
    started: bool = False
    stopped: bool = False
    continued: bool = False
    all_notes_off_called: bool = False  # Phase 2: Track all_notes_off calls
    _connected: bool = True
    _port_name: str | None = None

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    @property
    def port_name(self) -> str | None:
        return self._port_name

    def set_port(self, port_name: str) -> bool:
        self._port_name = port_name
        return True

    def send_note_on(self, channel: int, note: int, velocity: int) -> bool:
        self.notes.append(("on", channel, note, velocity))
        return True

    def send_note_off(self, channel: int, note: int) -> bool:
        self.notes.append(("off", channel, note, 0))
        return True

    def send_cc(self, channel: int, cc: int, value: int) -> bool:
        self.cc_messages.append((channel, cc, value))
        return True

    def send_pitch_bend(self, channel: int, value: int) -> bool:
        self.pitch_bends.append((channel, value))
        return True

    def send_aftertouch(self, channel: int, value: int) -> bool:
        self.aftertouches.append((channel, value))
        return True

    def send_clock(self) -> bool:
        self.clocks += 1
        return True

    def send_start(self) -> bool:
        self.started = True
        return True

    def send_stop(self) -> bool:
        self.stopped = True
        return True

    def send_continue(self) -> bool:
        self.continued = True
        return True

    def all_notes_off(self, channel: int | None = None) -> bool:
        self.all_notes_off_called = True
        return True

    @property
    def is_connected(self) -> bool:
        return self._connected

    def reset(self) -> None:
        """Reset all recorded state for next test."""
        self.notes.clear()
        self.cc_messages.clear()
        self.pitch_bends.clear()
        self.aftertouches.clear()
        self.clocks = 0
        self.started = False
        self.stopped = False
        self.continued = False
        self.all_notes_off_called = False


@dataclass
class MockOscOutput:
    """
    Test double for OscOutput protocol.

    Records all OSC events for test assertions.
    """

    osc_events: list = field(default_factory=list)  # list[OscEvent]
    _connected: bool = True

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def send_osc_event(self, event: OscEvent) -> bool:
        """Records OscEvent directly."""
        self.osc_events.append(event)
        return True

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def events(self) -> list:
        """Alias for osc_events (backward compatibility)."""
        return self.osc_events

    def reset(self) -> None:
        """Reset all recorded state for next test."""
        self.osc_events.clear()


@dataclass
class MockCommandSource:
    """
    Test double for CommandSource protocol.

    Allows injecting commands from tests.
    """

    commands: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    _handlers: dict[str, Callable[[dict[str, Any]], None]] = field(default_factory=dict)
    _connected: bool = True

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def register_handler(
        self,
        command_type: str,
        handler: Callable[[dict[str, Any]], None],
    ) -> None:
        self._handlers[command_type] = handler

    async def receive(self) -> tuple[str, dict[str, Any]] | None:
        if self.commands:
            return self.commands.pop(0)
        return None

    async def process_commands(self) -> int:
        """Process all pending commands using registered handlers."""
        processed = 0
        while self.commands:
            cmd_type, payload = self.commands.pop(0)
            handler = self._handlers.get(cmd_type)
            if handler:
                handler(payload)
                processed += 1
        return processed

    def inject_command(self, cmd_type: str, payload: dict[str, Any] | None = None) -> None:
        """Inject a command from test code."""
        self.commands.append((cmd_type, payload or {}))

    @property
    def is_connected(self) -> bool:
        return self._connected

    def reset(self) -> None:
        """Reset all recorded state for next test."""
        self.commands.clear()
        self._handlers.clear()


@dataclass
class MockStateSink:
    """
    Test double for StateSink protocol.

    Records all published state messages for test assertions.
    """

    messages: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    positions: list[dict[str, Any]] = field(default_factory=list)
    _connected: bool = True

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    async def send(self, msg_type: str, payload: dict[str, Any]) -> None:
        self.messages.append((msg_type, payload))

    async def send_position(
        self,
        position: dict[str, Any],
        bpm: float | None = None,
        transport: str | None = None,
    ) -> None:
        payload = {**position}
        if bpm is not None:
            payload["bpm"] = bpm
        if transport is not None:
            payload["transport"] = transport
        self.positions.append(payload)
        await self.send("position", payload)

    async def send_status(
        self,
        transport: str,
        bpm: float,
        active_tracks: list[str],
    ) -> None:
        """Send status update."""
        await self.send("status", {
            "transport": transport,
            "bpm": bpm,
            "active_tracks": active_tracks,
        })

    async def send_error(self, code: str, message: str) -> None:
        """Send error notification."""
        await self.send("error_msg", {
            "code": code,
            "message": message,
        })

    async def send_tracks(self, tracks: list[dict[str, Any]]) -> None:
        """Send track information."""
        await self.send("tracks", {"tracks": tracks})

    @property
    def is_connected(self) -> bool:
        return self._connected

    def reset(self) -> None:
        """Reset all recorded state for next test."""
        self.messages.clear()
        self.positions.clear()

    def get_messages_by_type(self, msg_type: str) -> list[dict[str, Any]]:
        """Get all messages of a specific type."""
        return [payload for t, payload in self.messages if t == msg_type]
