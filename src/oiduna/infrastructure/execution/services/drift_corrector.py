"""
Drift Corrector Service

Handles clock drift detection and correction using anchor-based timing.
Inspired by TidalCycles' clockSkipTicks mechanism.

Martin Fowler patterns applied:
- Extract Class: Separated drift logic from LoopEngine/ClockGenerator
- Single Responsibility Principle: Only handles drift detection/correction
- Protocol-based Dependency Injection: DriftNotifier for notifications
"""

from __future__ import annotations

import logging
import time
from typing import Protocol

logger = logging.getLogger(__name__)


class DriftNotifier(Protocol):
    """
    Protocol for drift reset notifications.

    Allows DriftCorrector to notify about drift events without
    coupling to specific notification implementations.
    """

    async def send_error(self, error_code: str, message: str) -> None:
        """
        Send an error notification.

        Args:
            error_code: Error code identifier (e.g., "CLOCK_DRIFT_RESET")
            message: Human-readable error message
        """
        ...


class DriftCorrector:
    """
    Manages clock drift detection and correction.

    Uses anchor-based timing to track expected vs actual execution times.
    Automatically resets anchor when drift exceeds threshold to prevent
    burst playback (inspired by TidalCycles' clockSkipTicks).

    Single responsibility: Clock drift management
    """

    # Default thresholds
    DEFAULT_RESET_THRESHOLD_MS = 50.0  # Reset if drift exceeds 50ms
    DEFAULT_WARNING_THRESHOLD_MS = 20.0  # Log warning if drift exceeds 20ms

    def __init__(
        self,
        reset_threshold_ms: float = DEFAULT_RESET_THRESHOLD_MS,
        warning_threshold_ms: float = DEFAULT_WARNING_THRESHOLD_MS,
        notifier: DriftNotifier | None = None,
    ):
        """
        Initialize drift corrector.

        Args:
            reset_threshold_ms: Drift threshold for anchor reset (milliseconds)
            warning_threshold_ms: Drift threshold for warnings (milliseconds)
            notifier: Optional notifier for drift reset events
        """
        self.reset_threshold_ms = reset_threshold_ms
        self.warning_threshold_ms = warning_threshold_ms
        self._notifier = notifier

        # Anchor state
        self._anchor_time: float | None = None
        self._count: int = 0

        # BPM change grace: suppress next drift reset notification
        self._suppress_next_reset = False

        # Statistics
        self._stats: dict[str, float | int] = {
            "reset_count": 0,
            "max_drift_ms": 0.0,
            "total_skipped_steps": 0,
            "last_reset_drift_ms": 0.0,
        }

    def reset(self) -> None:
        """Reset drift correction state (called when playback stops)."""
        self._anchor_time = None
        self._count = 0

    def suppress_next_reset(self) -> None:
        """
        Suppress the next drift reset notification.

        Called when BPM changes during playback to avoid false positives
        from timing transitions. Uses flag-based suppression to avoid
        async timing race conditions.
        """
        if self._anchor_time is not None:
            current_time = time.perf_counter()
            self._anchor_time = current_time
            self._count = 0
            self._suppress_next_reset = True
            logger.debug("Drift anchor reset (suppression enabled for BPM change)")

    async def check_drift(
        self,
        interval_duration: float,
        context_name: str = "clock",
    ) -> tuple[bool, float]:
        """
        Check for clock drift and handle if necessary.

        Args:
            interval_duration: Expected duration between ticks (seconds)
            context_name: Context for logging (e.g., "step", "midi_clock")

        Returns:
            Tuple of (should_reset, drift_ms):
            - should_reset: True if anchor was reset due to excessive drift
            - drift_ms: Current drift in milliseconds
        """
        # Initialize anchor on first call or after reset
        if self._anchor_time is None:
            self._anchor_time = time.perf_counter()
            self._count = 0
            return (False, 0.0)

        current_time = time.perf_counter()

        # Calculate drift
        expected_time = self._anchor_time + (self._count * interval_duration)
        drift_seconds = current_time - expected_time
        drift_ms = drift_seconds * 1000

        # Update max drift statistic
        if abs(drift_ms) > self._stats["max_drift_ms"]:
            self._stats["max_drift_ms"] = abs(drift_ms)

        # Check for excessive drift
        if abs(drift_ms) > self.reset_threshold_ms:
            if self._suppress_next_reset:
                # Suppress notification after BPM change
                self._anchor_time = current_time
                self._count = 0
                self._suppress_next_reset = False
                logger.debug(
                    f"{context_name} drift {drift_ms:.1f}ms suppressed (BPM change transition)"
                )
            else:
                # Normal case: report drift reset
                await self._handle_drift_reset(drift_ms, current_time, interval_duration, context_name)

            # After reset, set count to 1 to prevent infinite reset loop
            self._count = 1
            return (True, drift_ms)

        elif abs(drift_ms) > self.warning_threshold_ms:
            # Warning level drift - log but continue with normal correction
            logger.debug(f"{context_name} drift warning: {drift_ms:.1f}ms")

        return (False, drift_ms)

    async def _handle_drift_reset(
        self,
        drift_ms: float,
        current_time: float,
        interval_duration: float,
        context_name: str,
    ) -> None:
        """
        Handle large clock drift by resetting the anchor.

        Args:
            drift_ms: Detected drift in milliseconds
            current_time: Current perf_counter time
            interval_duration: Expected interval duration (seconds)
            context_name: Context for logging
        """
        # Calculate how many intervals would be skipped
        skipped = int(abs(drift_ms) / (interval_duration * 1000))

        # Determine drift direction for logging
        direction = "behind" if drift_ms > 0 else "ahead"

        logger.warning(
            f"{context_name} drift reset: {drift_ms:.1f}ms {direction}, "
            f"skipping ~{skipped} intervals (threshold: {self.reset_threshold_ms}ms)"
        )

        # Update statistics
        self._stats["reset_count"] = int(self._stats["reset_count"]) + 1
        self._stats["total_skipped_steps"] = (
            int(self._stats["total_skipped_steps"]) + skipped
        )
        self._stats["last_reset_drift_ms"] = drift_ms

        # Reset anchor to current time
        self._anchor_time = current_time
        self._count = 0

        # Notify about the drift reset
        if self._notifier:
            await self._notifier.send_error(
                "CLOCK_DRIFT_RESET",
                f"Clock resynchronized (drift: {drift_ms:.1f}ms {direction}, skipped: ~{skipped} intervals)"
            )

    def advance(self) -> None:
        """Advance the counter after successful interval."""
        self._count += 1

    def get_expected_time_with_offset(
        self,
        interval_duration: float,
        offset: float = 0.0
    ) -> float:
        """
        Get expected time for next interval with sub-step offset.

        Core timing calculation for offset support.

        Args:
            interval_duration: Expected duration between intervals (seconds)
            offset: Relative position within interval [0.0, 1.0)

        Returns:
            Expected time for interval with offset applied (perf_counter)
        """
        if self._anchor_time is None:
            return time.perf_counter()

        # Base expected time (start of step)
        base_time = self._anchor_time + (self._count * interval_duration)

        # Add offset within step
        offset_adjustment = interval_duration * offset

        return base_time + offset_adjustment

    def get_expected_next_time(self, interval_duration: float) -> float:
        """
        Get the expected time for the next interval (start of step).

        Args:
            interval_duration: Expected duration between intervals (seconds)

        Returns:
            Expected time for next interval (perf_counter)
        """
        return self.get_expected_time_with_offset(interval_duration, offset=0.0)

    def get_stats(self) -> dict[str, float | int]:
        """
        Get drift correction statistics.

        Returns:
            Dictionary with drift statistics:
            - reset_count: Number of times anchor was reset
            - max_drift_ms: Maximum drift observed
            - total_skipped_steps: Approximate total intervals skipped
            - last_reset_drift_ms: Drift value at last reset
            - current_count: Current count since last anchor
            - anchor_age_seconds: Time since anchor was set
        """
        return {
            **self._stats,
            "current_count": self._count,
            "anchor_age_seconds": (
                time.perf_counter() - self._anchor_time
                if self._anchor_time else 0.0
            ),
        }
