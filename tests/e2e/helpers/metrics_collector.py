"""Metrics collector for E2E tests."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TimingMetrics:
    """Timing metrics with statistical analysis."""

    intervals: list[float] = field(default_factory=list)

    @property
    def mean_ms(self) -> float:
        """Mean interval in milliseconds."""
        if not self.intervals:
            return 0.0
        return (sum(self.intervals) / len(self.intervals)) * 1000

    @property
    def stdev_ms(self) -> float:
        """Standard deviation in milliseconds."""
        if len(self.intervals) < 2:
            return 0.0
        mean = sum(self.intervals) / len(self.intervals)
        variance = sum((x - mean) ** 2 for x in self.intervals) / len(self.intervals)
        return (variance ** 0.5) * 1000

    @property
    def max_ms(self) -> float:
        """Maximum interval in milliseconds."""
        if not self.intervals:
            return 0.0
        return max(self.intervals) * 1000

    @property
    def min_ms(self) -> float:
        """Minimum interval in milliseconds."""
        if not self.intervals:
            return 0.0
        return min(self.intervals) * 1000


class MetricsCollector:
    """Collect and analyze timing and message metrics during E2E tests."""

    def __init__(self):
        """Initialize metrics collector."""
        self._step_times: list[float] = []
        self._last_step_time: float | None = None
        self._message_send_times: list[float] = []
        self._command_sent_times: list[float] = []
        self._command_processed_times: list[float] = []

    def record_step(self) -> None:
        """Record a step occurrence."""
        now = time.perf_counter()
        if self._last_step_time is not None:
            self._step_times.append(now - self._last_step_time)
        self._last_step_time = now

    def record_message_send(self) -> None:
        """Record a message send event."""
        self._message_send_times.append(time.perf_counter())

    def record_command_sent(self) -> None:
        """Record a command sent event."""
        self._command_sent_times.append(time.perf_counter())

    def record_command_processed(self) -> None:
        """Record a command processed event."""
        self._command_processed_times.append(time.perf_counter())

    def get_step_timing_metrics(self) -> TimingMetrics:
        """Get step timing metrics.

        Returns:
            TimingMetrics with step intervals
        """
        return TimingMetrics(intervals=self._step_times.copy())

    def get_command_latency_metrics(self) -> TimingMetrics:
        """Get command latency metrics.

        Returns:
            TimingMetrics with command latencies (sent to processed)
        """
        if len(self._command_sent_times) != len(self._command_processed_times):
            return TimingMetrics()

        latencies = [
            proc - sent
            for sent, proc in zip(
                self._command_sent_times, self._command_processed_times
            )
        ]
        return TimingMetrics(intervals=latencies)

    def assert_timing_accuracy(
        self,
        expected_interval_ms: float,
        max_deviation_ms: float,
        max_mean_deviation_ms: float,
    ) -> None:
        """Assert timing accuracy meets requirements.

        Args:
            expected_interval_ms: Expected interval in milliseconds
            max_deviation_ms: Maximum allowed deviation for any single interval
            max_mean_deviation_ms: Maximum allowed mean deviation

        Raises:
            AssertionError: If timing accuracy requirements not met
        """
        metrics = self.get_step_timing_metrics()

        if not metrics.intervals:
            raise AssertionError("No timing data collected")

        # Check mean deviation
        mean_deviation = abs(metrics.mean_ms - expected_interval_ms)
        assert mean_deviation <= max_mean_deviation_ms, (
            f"Mean deviation {mean_deviation:.2f}ms exceeds threshold "
            f"{max_mean_deviation_ms}ms (expected {expected_interval_ms}ms, "
            f"got {metrics.mean_ms:.2f}ms)"
        )

        # Check individual deviations
        max_individual_deviation = max(
            abs(interval * 1000 - expected_interval_ms)
            for interval in metrics.intervals
        )
        assert max_individual_deviation <= max_deviation_ms, (
            f"Max individual deviation {max_individual_deviation:.2f}ms exceeds "
            f"threshold {max_deviation_ms}ms"
        )

    def reset(self) -> None:
        """Reset all collected metrics."""
        self._step_times.clear()
        self._last_step_time = None
        self._message_send_times.clear()
        self._command_sent_times.clear()
        self._command_processed_times.clear()
