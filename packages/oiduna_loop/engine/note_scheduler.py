"""
Note Scheduler

Handles MIDI note scheduling and note-off timing.
Martin Fowler: Extract Class, Single Responsibility Principle.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from ..protocols import MidiOutput

logger = logging.getLogger(__name__)


@dataclass
class PendingNoteOff:
    """Scheduled note-off event"""
    off_time: float
    channel: int
    note: int


class NoteScheduler:
    """
    Schedules MIDI note-on and manages note-off timing.

    Single responsibility: MIDI note lifecycle management.
    """

    def __init__(self, midi: MidiOutput):
        """
        Initialize note scheduler.

        Args:
            midi: MIDI output (MidiSender or mock)
        """
        self._midi = midi
        self._pending_note_offs: list[PendingNoteOff] = []

    def schedule_note_on_channel(
        self,
        channel: int,
        note: int,
        velocity: int,
        step_duration: float,
        gate: float = 1.0,
    ) -> None:
        """
        Schedule a MIDI note with automatic note-off.

        Args:
            channel: MIDI channel (0-15)
            note: MIDI note number
            velocity: Note velocity (0-127)
            step_duration: Current step duration in seconds
            gate: Gate length in steps
        """
        if not self._midi.is_connected:
            return

        # Send note on
        self._midi.send_note_on(channel, note, velocity)

        # Schedule note off (gate is in steps, step_duration is seconds/step)
        note_off_time = time.perf_counter() + (step_duration * gate)
        self._pending_note_offs.append(PendingNoteOff(
            off_time=note_off_time,
            channel=channel,
            note=note,
        ))

    def process_pending_note_offs(self) -> None:
        """
        Process all due note-off events.

        Uses in-place list modification with reverse iteration to avoid
        creating new list objects on every call (reduces GC pressure).
        """
        if not self._midi.is_connected:
            return

        current_time = time.perf_counter()

        # Reverse iteration: pop() doesn't affect indices of earlier elements
        i = len(self._pending_note_offs) - 1
        while i >= 0:
            pending = self._pending_note_offs[i]
            if current_time >= pending.off_time:
                self._midi.send_note_off(pending.channel, pending.note)
                self._pending_note_offs.pop(i)
            i -= 1

    def clear_all(self) -> None:
        """Clear all pending note-offs and send note-off for all."""
        self._pending_note_offs.clear()
        self._midi.all_notes_off()

    @property
    def pending_count(self) -> int:
        """Number of pending note-off events."""
        return len(self._pending_note_offs)

    def get_next_off_time(self) -> float | None:
        """
        Get the earliest pending note-off time.

        Returns:
            The earliest off_time in seconds (perf_counter), or None if no notes pending.

        Used by LoopEngine to implement adaptive sleep in _note_off_loop,
        reducing CPU usage from 1000 polls/sec to event-driven timing.
        Inspired by TidalCycles' clockFrameTimespan approach.
        """
        if not self._pending_note_offs:
            return None
        return min(note.off_time for note in self._pending_note_offs)
