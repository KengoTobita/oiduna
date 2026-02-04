"""
Clock Generator

Handles MIDI clock generation at 24 PPQ.
Martin Fowler: Extract Class, Single Responsibility Principle.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from typing import TYPE_CHECKING

from ..protocols import MidiOutput

if TYPE_CHECKING:
    from ..state import RuntimeState

logger = logging.getLogger(__name__)


class ClockGenerator:
    """
    Generates MIDI clock at 24 PPQ (Pulses Per Quarter note).

    Single responsibility: MIDI clock timing generation.
    """

    MIDI_PPQ = 24  # Pulses Per Quarter note
    PULSES_PER_STEP = 6  # 24 PPQ / 4 steps per quarter note

    # Drift reset configuration (similar to LoopEngine)
    # Clock runs at higher frequency, so use proportionally smaller threshold
    DRIFT_RESET_THRESHOLD_MS: float = 30.0  # Reset if drift exceeds 30ms
    DRIFT_WARNING_THRESHOLD_MS: float = 15.0  # Log warning if drift exceeds 15ms

    def __init__(self, midi: MidiOutput):
        """
        Initialize clock generator.

        Args:
            midi: MIDI output (MidiSender or mock)
        """
        self._midi = midi

        # Drift correction state (Phase 1)
        self._clock_anchor_time: float | None = None
        self._pulse_count: int = 0

        # BPM change: suppress next drift reset during transitions
        self._suppress_next_drift_reset: bool = False

        # Drift reset statistics
        self._drift_stats: dict[str, float | int] = {
            "reset_count": 0,
            "max_drift_ms": 0.0,
        }

    def send_start(self) -> None:
        """Send MIDI Start message."""
        if self._midi.is_connected:
            self._midi.send_start()

    def send_stop(self) -> None:
        """Send MIDI Stop message."""
        if self._midi.is_connected:
            self._midi.send_stop()

    def send_continue(self) -> None:
        """Send MIDI Continue message."""
        if self._midi.is_connected:
            self._midi.send_continue()

    def suppress_next_drift_reset(self) -> None:
        """
        Suppress the next drift reset notification for BPM transitions.

        Called by LoopEngine when BPM changes during playback.
        Uses flag-based suppression to avoid async timing race conditions.
        """
        if self._clock_anchor_time is not None:
            current_time = time.perf_counter()
            self._clock_anchor_time = current_time
            self._pulse_count = 0
            self._suppress_next_drift_reset = True
            logger.debug("MIDI clock anchor reset (drift suppression enabled)")

    async def run_clock_loop(
        self,
        state: RuntimeState,
        running_flag: Callable[[], bool],
    ) -> None:
        """
        Run the 24 PPQ MIDI clock loop with drift correction and auto-reset.

        Args:
            state: Session state for timing info
            running_flag: Callable returning True while loop should run

        Drift correction (Phase 1):
        - Uses anchor time to calculate expected pulse times
        - Compensates for accumulated drift over many pulses

        Drift reset (inspired by Tidal's clockSkipTicks):
        - If drift exceeds threshold, reset anchor instead of catching up
        - Prevents burst MIDI clock messages after CPU spikes
        """
        if not self._midi.is_connected:
            return

        while running_flag():
            if not state.playing:
                # Reset anchor when not playing
                self._clock_anchor_time = None
                self._pulse_count = 0
                await asyncio.sleep(0.001)
                continue

            # Initialize anchor time when playback starts
            if self._clock_anchor_time is None:
                self._clock_anchor_time = time.perf_counter()
                self._pulse_count = 0

            # Calculate pulse duration
            pulse_duration = self.calculate_pulse_duration(state.step_duration)
            current_time = time.perf_counter()

            # === Drift detection ===
            expected_time = self._clock_anchor_time + (self._pulse_count * pulse_duration)
            drift_seconds = current_time - expected_time
            drift_ms = drift_seconds * 1000

            # Update max drift statistic
            if abs(drift_ms) > self._drift_stats["max_drift_ms"]:
                self._drift_stats["max_drift_ms"] = abs(drift_ms)

            # === Drift reset logic ===
            if abs(drift_ms) > self.DRIFT_RESET_THRESHOLD_MS:
                if self._suppress_next_drift_reset:
                    # Suppress notification after BPM change (expected drift)
                    self._clock_anchor_time = current_time
                    self._pulse_count = 0
                    self._suppress_next_drift_reset = False
                    logger.debug(
                        f"MIDI clock drift {drift_ms:.1f}ms suppressed (BPM change transition)"
                    )
                else:
                    # Normal case: log warning and reset
                    self._handle_drift_reset(drift_ms, current_time)

                # After reset, we're about to sleep for one pulse_duration.
                # Set pulse_count to 1 so next iteration expects: anchor + 1 * pulse_duration
                # This prevents infinite reset loop where drift = sleep_time each iteration.
                self._pulse_count = 1

                await asyncio.sleep(pulse_duration)
                continue
            elif abs(drift_ms) > self.DRIFT_WARNING_THRESHOLD_MS:
                logger.debug(f"MIDI clock drift warning: {drift_ms:.1f}ms")

            # Send MIDI clock pulse
            self._midi.send_clock()

            # Advance pulse count
            self._pulse_count += 1

            # Drift-corrected wait: calculate expected time for next pulse
            expected_next = self._clock_anchor_time + (self._pulse_count * pulse_duration)
            wait_time = max(0, expected_next - time.perf_counter())
            await asyncio.sleep(wait_time)

    def _handle_drift_reset(self, drift_ms: float, current_time: float) -> None:
        """
        Handle large clock drift by resetting the anchor.

        Args:
            drift_ms: Detected drift in milliseconds
            current_time: Current perf_counter time
        """
        direction = "behind" if drift_ms > 0 else "ahead"
        logger.warning(
            f"MIDI clock drift reset: {drift_ms:.1f}ms {direction} "
            f"(threshold: {self.DRIFT_RESET_THRESHOLD_MS}ms)"
        )

        # Update statistics
        self._drift_stats["reset_count"] = int(self._drift_stats["reset_count"]) + 1

        # Reset anchor
        self._clock_anchor_time = current_time
        self._pulse_count = 0

    def get_drift_stats(self) -> dict[str, float | int]:
        """Get drift statistics for monitoring."""
        return {
            **self._drift_stats,
            "current_pulse_count": self._pulse_count,
        }

    def calculate_pulse_duration(self, step_duration: float) -> float:
        """
        Calculate MIDI clock pulse duration from step duration.

        Args:
            step_duration: Duration of one step (16th note) in seconds

        Returns:
            Duration of one MIDI clock pulse in seconds
        """
        return step_duration / self.PULSES_PER_STEP
