"""
Unit tests for DriftCorrector service.
"""

import asyncio
import time
import pytest
from oiduna.infrastructure.execution.services.drift_corrector import DriftCorrector, DriftNotifier


class MockNotifier:
    """Mock notifier for testing."""

    def __init__(self):
        self.errors = []

    async def send_error(self, error_code: str, message: str) -> None:
        """Record error notifications."""
        self.errors.append({"code": error_code, "message": message})


@pytest.fixture
def notifier():
    """Create mock notifier."""
    return MockNotifier()


@pytest.fixture
def corrector(notifier):
    """Create drift corrector with mock notifier."""
    return DriftCorrector(
        reset_threshold_ms=50.0,
        warning_threshold_ms=20.0,
        notifier=notifier,
    )


class TestDriftCorrectorBasics:
    """Test basic drift corrector operations."""

    def test_initialization(self, corrector):
        """Test corrector initializes with correct defaults."""
        assert corrector.reset_threshold_ms == 50.0
        assert corrector.warning_threshold_ms == 20.0
        stats = corrector.get_stats()
        assert stats["reset_count"] == 0
        assert stats["max_drift_ms"] == 0.0

    def test_reset(self, corrector):
        """Test reset clears state."""
        # Advance some counts
        corrector.advance()
        corrector.advance()
        # Reset
        corrector.reset()
        stats = corrector.get_stats()
        assert stats["current_count"] == 0
        assert stats["anchor_age_seconds"] == 0.0


class TestDriftDetection:
    """Test drift detection logic."""

    @pytest.mark.asyncio
    async def test_no_drift_on_first_check(self, corrector):
        """First check should initialize anchor with no drift."""
        should_reset, drift_ms = await corrector.check_drift(0.01, "test")
        assert should_reset is False
        assert drift_ms == 0.0

    @pytest.mark.asyncio
    async def test_small_drift_no_reset(self, corrector):
        """Small drift should not trigger reset."""
        # Initialize
        await corrector.check_drift(0.01, "test")
        corrector.advance()

        # Sleep less than expected (5ms instead of 10ms)
        await asyncio.sleep(0.005)
        should_reset, drift_ms = await corrector.check_drift(0.01, "test")

        # Drift should be detected but not trigger reset
        assert should_reset is False
        assert drift_ms < 0  # We're ahead of schedule

    @pytest.mark.asyncio
    async def test_large_drift_triggers_reset(self, corrector, notifier):
        """Large drift should trigger anchor reset."""
        # Initialize
        await corrector.check_drift(0.01, "test")
        corrector.advance()

        # Sleep much longer than expected to cause large drift
        await asyncio.sleep(0.060)  # 60ms sleep for 10ms interval = 50ms+ drift
        should_reset, drift_ms = await corrector.check_drift(0.01, "test")

        # Should trigger reset
        assert should_reset is True
        assert abs(drift_ms) > 50.0

        # Should send notification
        assert len(notifier.errors) == 1
        assert notifier.errors[0]["code"] == "CLOCK_DRIFT_RESET"

    @pytest.mark.asyncio
    async def test_suppressed_reset_no_notification(self, corrector, notifier):
        """Suppressed reset should not send notification."""
        # Initialize
        await corrector.check_drift(0.01, "test")
        corrector.advance()

        # Suppress next reset (e.g., BPM change)
        corrector.suppress_next_reset()

        # Sleep to cause large drift
        await asyncio.sleep(0.060)
        should_reset, drift_ms = await corrector.check_drift(0.01, "test")

        # Should still detect drift but not notify
        assert should_reset is True
        assert len(notifier.errors) == 0  # No notification


class TestDriftStatistics:
    """Test drift statistics tracking."""

    @pytest.mark.asyncio
    async def test_max_drift_tracking(self, corrector):
        """Test max drift is tracked correctly."""
        # Initialize
        await corrector.check_drift(0.01, "test")
        corrector.advance()

        # Create some drift
        await asyncio.sleep(0.015)  # 15ms for 10ms interval
        await corrector.check_drift(0.01, "test")

        stats = corrector.get_stats()
        assert stats["max_drift_ms"] > 0

    @pytest.mark.asyncio
    async def test_reset_count_increments(self, corrector):
        """Test reset count increments on each reset."""
        initial_stats = corrector.get_stats()
        assert initial_stats["reset_count"] == 0

        # Cause drift reset
        await corrector.check_drift(0.01, "test")
        corrector.advance()
        await asyncio.sleep(0.060)
        await corrector.check_drift(0.01, "test")

        stats = corrector.get_stats()
        assert stats["reset_count"] == 1


class TestAdvanceAndTiming:
    """Test advance and timing calculations."""

    def test_advance_increments_count(self, corrector):
        """Test advance increments the counter."""
        initial_stats = corrector.get_stats()
        count_before = initial_stats["current_count"]

        corrector.advance()

        stats = corrector.get_stats()
        assert stats["current_count"] == count_before + 1

    @pytest.mark.asyncio
    async def test_expected_next_time(self, corrector):
        """Test expected next time calculation."""
        # Initialize
        await corrector.check_drift(0.01, "test")

        # Get expected next time
        next_time = corrector.get_expected_next_time(0.01)
        current_time = time.perf_counter()

        # Should be close to current time
        assert abs(next_time - current_time) < 0.02  # Within 20ms


class TestProtocolCompliance:
    """Test Protocol-based dependency injection."""

    @pytest.mark.asyncio
    async def test_works_without_notifier(self):
        """Test corrector works without a notifier."""
        corrector = DriftCorrector(notifier=None)

        # Should not raise even without notifier
        await corrector.check_drift(0.01, "test")
        corrector.advance()
        await asyncio.sleep(0.060)
        should_reset, _ = await corrector.check_drift(0.01, "test")

        assert should_reset is True  # Drift detected even without notifier
