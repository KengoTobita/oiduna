"""High-level assertion helpers for E2E tests."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from oiduna.infrastructure.execution import LoopEngine


class E2EAssertions:
    """Semantic assertions for E2E test verification."""

    @staticmethod
    def assert_messages_sent(
        mock_osc: Any,
        expected_count: int,
        message: str = "Expected number of messages not sent",
    ) -> None:
        """Assert that expected number of messages were sent.

        Args:
            mock_osc: Mock OSC output
            expected_count: Expected message count
            message: Assertion message

        Raises:
            AssertionError: If message count doesn't match
        """
        actual_count = len(mock_osc.get_sent_messages())
        assert actual_count == expected_count, (
            f"{message}: expected {expected_count}, got {actual_count}"
        )

    @staticmethod
    def assert_playback_state(
        engine: LoopEngine,
        expected_state: Any,
        message: str = "Expected playback state not reached",
    ) -> None:
        """Assert engine playback state.

        Args:
            engine: Loop engine instance
            expected_state: Expected PlaybackState
            message: Assertion message

        Raises:
            AssertionError: If state doesn't match
        """
        actual_state = engine.state.transport
        assert actual_state == expected_state, (
            f"{message}: expected {expected_state}, got {actual_state}"
        )

    @staticmethod
    def assert_position_advanced(
        mock_publisher: Any,
        min_positions: int = 1,
    ) -> None:
        """Assert that position updates were published.

        Args:
            mock_publisher: Mock state publisher
            min_positions: Minimum number of position updates expected

        Raises:
            AssertionError: If position updates below minimum
        """
        position_updates = mock_publisher.get_position_updates()
        assert len(position_updates) >= min_positions, (
            f"Expected at least {min_positions} position updates, "
            f"got {len(position_updates)}"
        )

    @staticmethod
    def assert_no_errors_published(mock_publisher: Any) -> None:
        """Assert that no errors were published.

        Args:
            mock_publisher: Mock state publisher

        Raises:
            AssertionError: If any errors were published
        """
        errors = mock_publisher.get_error_messages()
        assert len(errors) == 0, f"Expected no errors, but got {len(errors)}: {errors}"

    @staticmethod
    def assert_drift_within_threshold(
        engine: LoopEngine,
        max_drift_ms: float = 50.0,
    ) -> None:
        """Assert that drift stays within threshold.

        Args:
            engine: Loop engine instance
            max_drift_ms: Maximum allowed drift in milliseconds

        Raises:
            AssertionError: If drift exceeds threshold
        """
        actual_drift = engine._drift_corrector._stats.get("max_drift_ms", 0.0)
        assert actual_drift <= max_drift_ms, (
            f"Drift {actual_drift:.2f}ms exceeds threshold {max_drift_ms}ms"
        )

    @staticmethod
    def assert_no_drift_resets(engine: LoopEngine) -> None:
        """Assert that no drift resets occurred.

        Args:
            engine: Loop engine instance

        Raises:
            AssertionError: If drift resets occurred
        """
        resets = engine._drift_corrector._stats.get("reset_count", 0)
        assert resets == 0, f"Expected 0 drift resets, got {resets}"

    @staticmethod
    def assert_command_processed(
        mock_publisher: Any,
        expected_status_change: bool = True,
    ) -> None:
        """Assert that command was processed (status changed).

        Args:
            mock_publisher: Mock state publisher
            expected_status_change: Whether status change is expected

        Raises:
            AssertionError: If status change expectation not met
        """
        status_updates = mock_publisher.get_status_updates()
        if expected_status_change:
            assert len(status_updates) > 0, "Expected status update after command"
        else:
            assert len(status_updates) == 0, "Expected no status update"
