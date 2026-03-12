"""
Clock Generator

Handles MIDI clock generation at 24 PPQ.
Martin Fowler: Extract Class, Single Responsibility Principle.

Phase 2: Refactored to use DriftCorrector service.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from oiduna.infrastructure.transport.protocols import MidiOutput
from .services import DriftCorrector

if TYPE_CHECKING:
    from .state.runtime_state import RuntimeState

logger = logging.getLogger(__name__)


class ClockGenerator:
    """
    Generates MIDI clock at 24 PPQ (Pulses Per Quarter note).

    Single responsibility: MIDI clock timing generation.
    Phase 2: Uses DriftCorrector service for timing management.
    """

    MIDI_PPQ = 24  # Pulses Per Quarter note
    PULSES_PER_STEP = 6  # 24 PPQ / 4 steps per quarter note

    # Drift thresholds for MIDI clock (higher frequency than step loop)
    DRIFT_RESET_THRESHOLD_MS: float = 30.0  # Reset if drift exceeds 30ms
    DRIFT_WARNING_THRESHOLD_MS: float = 15.0  # Log warning if drift exceeds 15ms

    def __init__(self, midi: MidiOutput):
        """
        Initialize clock generator.

        Args:
            midi: MIDI output (MidiSender or mock)
        """
        self._midi = midi

        # Drift correction (Phase 2: Extracted to service)
        self._drift_corrector = DriftCorrector(
            reset_threshold_ms=self.DRIFT_RESET_THRESHOLD_MS,
            warning_threshold_ms=self.DRIFT_WARNING_THRESHOLD_MS,
            notifier=None,  # Clock drift is silent (only step loop notifies)
        )

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
        self._drift_corrector.suppress_next_reset()

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

        Phase 2: Uses DriftCorrector service for timing management.
        """
        if not self._midi.is_connected:
            return

        while running_flag():
            if not state.playing:
                # Reset drift corrector when not playing
                self._drift_corrector.reset()
                await asyncio.sleep(0.001)
                continue

            # Calculate pulse duration
            pulse_duration = self.calculate_pulse_duration(state.step_duration)

            # Check for drift (DriftCorrector handles anchor initialization)
            should_reset, drift_ms = await self._drift_corrector.check_drift(
                pulse_duration,
                "MIDI clock",
            )

            if should_reset:
                # Large drift detected, anchor was reset
                # Wait one pulse duration before continuing
                await asyncio.sleep(pulse_duration)
                continue

            # Send MIDI clock pulse
            self._midi.send_clock()

            # Advance drift corrector counter
            self._drift_corrector.advance()

            # Drift-corrected wait: calculate expected time for next pulse
            import time
            expected_next = self._drift_corrector.get_expected_next_time(pulse_duration)
            wait_time = max(0, expected_next - time.perf_counter())
            await asyncio.sleep(wait_time)

    def get_drift_stats(self) -> dict[str, float | int]:
        """Get drift statistics for monitoring (delegated to DriftCorrector)."""
        stats = self._drift_corrector.get_stats()
        # Rename 'current_count' to 'current_pulse_count' for backward compatibility
        stats["current_pulse_count"] = stats.pop("current_count")
        return stats

    def calculate_pulse_duration(self, step_duration: float) -> float:
        """
        Calculate MIDI clock pulse duration from step duration.

        Args:
            step_duration: Duration of one step (16th note) in seconds

        Returns:
            Duration of one MIDI clock pulse in seconds
        """
        return step_duration / self.PULSES_PER_STEP
