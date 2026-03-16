"""
Unit tests for StepExecutor service.

Follows test pattern from test_drift_corrector.py.
"""

import asyncio
import pytest
from oiduna.infrastructure.execution.services.step_executor import (
    StepExecutor,
    MessageScheduler,
    MessageRouter,
    StatePublisher,
    MessageFilter,
    TimelineProvider,
)


class MockMessageScheduler:
    """Mock message scheduler for testing."""

    def __init__(self):
        self._messages = {}
        self._message_count = 0

    @property
    def message_count(self) -> int:
        return self._message_count

    def get_messages_at_step(self, step: int) -> list[dict]:
        return self._messages.get(step, [])

    def add_message(self, step: int, message: dict) -> None:
        """Add a message at a specific step."""
        if step not in self._messages:
            self._messages[step] = []
        self._messages[step].append(message)
        self._message_count += 1


class MockMessageRouter:
    """Mock message router for testing."""

    def __init__(self):
        self.sent_messages = []

    def send_messages(self, messages: list) -> None:
        self.sent_messages.extend(messages)

    def send_messages_with_timing(
        self,
        messages: list,
        offset: float,
        step_duration: float
    ) -> None:
        """Send messages with timing (mock implementation)."""
        # For testing, just send messages immediately
        self.sent_messages.extend(messages)


class MockStatePublisher:
    """Mock state publisher for testing."""

    def __init__(self):
        self.positions = []
        self.tracks = []
        self.errors = []

    async def send_position(self, position: dict, bpm: float, transport: str) -> None:
        self.positions.append({"position": position, "bpm": bpm, "transport": transport})

    async def send_tracks(self, tracks: list) -> None:
        self.tracks.append(tracks)

    async def send_error(self, error_code: str, message: str) -> None:
        self.errors.append({"code": error_code, "message": message})


class MockPosition:
    """Mock position for testing."""

    def __init__(self):
        self.step = 0
        self.bar = 0
        self.beat = 0
        self.timestamp = 0.0

    def to_dict(self):
        return {
            "step": self.step,
            "bar": self.bar,
            "beat": self.beat,
            "timestamp": self.timestamp,
        }


class MockPlaybackState:
    """Mock playback state for testing."""

    def __init__(self):
        self.value = "playing"


class MockMessageFilter:
    """Mock message filter for testing."""

    def __init__(self):
        self.muted_tracks = set()
        self.position = MockPosition()
        self.playback_state = MockPlaybackState()

    def filter_messages(self, messages: list) -> list:
        """Filter out messages from muted tracks."""
        return [m for m in messages if m.get("track") not in self.muted_tracks]


class MockTimelineProvider:
    """Mock timeline provider for testing."""

    def __init__(self):
        self._timeline = None
        self._global_step = 0

    @property
    def timeline(self):
        return self._timeline

    @property
    def global_step(self) -> int:
        return self._global_step


@pytest.fixture
def message_scheduler():
    """Create mock message scheduler."""
    return MockMessageScheduler()


@pytest.fixture
def message_router():
    """Create mock message router."""
    return MockMessageRouter()


@pytest.fixture
def state_publisher():
    """Create mock state publisher."""
    return MockStatePublisher()


@pytest.fixture
def message_filter():
    """Create mock message filter."""
    return MockMessageFilter()


@pytest.fixture
def timeline_provider():
    """Create mock timeline provider."""
    return MockTimelineProvider()


@pytest.fixture
def session_loaded():
    """Session loaded check function."""
    return lambda: True


@pytest.fixture
def get_tracks_info():
    """Get tracks info function."""
    return lambda: [{"track": "kick", "muted": False}]


@pytest.fixture
def executor(
    message_scheduler,
    message_router,
    state_publisher,
    message_filter,
    timeline_provider,
    session_loaded,
    get_tracks_info,
):
    """Create step executor with mocks."""
    return StepExecutor(
        message_scheduler=message_scheduler,
        message_router=message_router,
        state_publisher=state_publisher,
        message_filter=message_filter,
        timeline_provider=timeline_provider,
        session_loaded_check=session_loaded,
        get_tracks_info=get_tracks_info,
        position_update_interval="beat",
        before_send_hooks=[],
    )


class TestStepExecutorBasics:
    """Test basic step executor operations."""

    @pytest.mark.asyncio
    async def test_execute_step_no_messages(self, executor, message_router):
        """Execute step with no scheduled messages."""
        await executor.execute_step(0, 120.0)
        assert len(message_router.sent_messages) == 0

    @pytest.mark.asyncio
    async def test_execute_step_with_messages(
        self, executor, message_scheduler, message_router
    ):
        """Execute step with scheduled messages."""
        # Add message at step 0
        message_scheduler.add_message(0, {"track": "kick", "note": 36})

        await executor.execute_step(0, 120.0)

        # Message should be sent
        assert len(message_router.sent_messages) == 1
        assert message_router.sent_messages[0]["note"] == 36

    @pytest.mark.asyncio
    async def test_execute_step_wrong_step(
        self, executor, message_scheduler, message_router
    ):
        """Execute step that has no messages."""
        # Add message at step 0
        message_scheduler.add_message(0, {"track": "kick", "note": 36})

        # Execute step 1 (no messages)
        await executor.execute_step(1, 120.0)

        # No messages should be sent
        assert len(message_router.sent_messages) == 0

    @pytest.mark.asyncio
    async def test_execute_multiple_messages(
        self, executor, message_scheduler, message_router
    ):
        """Execute step with multiple messages."""
        message_scheduler.add_message(0, {"track": "kick", "note": 36})
        message_scheduler.add_message(0, {"track": "snare", "note": 38})

        await executor.execute_step(0, 120.0)

        assert len(message_router.sent_messages) == 2


class TestMessageFiltering:
    """Test message filtering (mute/solo)."""

    @pytest.mark.asyncio
    async def test_filter_muted_messages(
        self, executor, message_scheduler, message_filter, message_router
    ):
        """Muted track messages should be filtered out."""
        # Add messages
        message_scheduler.add_message(0, {"track": "kick", "note": 36})
        message_scheduler.add_message(0, {"track": "snare", "note": 38})

        # Mute kick track
        message_filter.muted_tracks.add("kick")

        await executor.execute_step(0, 120.0)

        # Only snare message should be sent
        assert len(message_router.sent_messages) == 1
        assert message_router.sent_messages[0]["track"] == "snare"

    @pytest.mark.asyncio
    async def test_filter_all_messages(
        self, executor, message_scheduler, message_filter, message_router
    ):
        """All messages filtered should send nothing."""
        message_scheduler.add_message(0, {"track": "kick", "note": 36})

        # Mute kick track
        message_filter.muted_tracks.add("kick")

        await executor.execute_step(0, 120.0)

        # No messages should be sent
        assert len(message_router.sent_messages) == 0


class TestHookApplication:
    """Test extension hook processing."""

    @pytest.mark.asyncio
    async def test_apply_hooks_modifies_messages(
        self, message_scheduler, message_router, message_filter, timeline_provider
    ):
        """Hooks should modify messages."""

        def transpose_hook(messages, bpm, step):
            """Example hook that transposes notes."""
            return [
                {**m, "note": m["note"] + 12} if "note" in m else m for m in messages
            ]

        executor = StepExecutor(
            message_scheduler=message_scheduler,
            message_router=message_router,
            state_publisher=MockStatePublisher(),
            message_filter=message_filter,
            timeline_provider=timeline_provider,
            session_loaded_check=lambda: True,
            get_tracks_info=lambda: [],
            before_send_hooks=[transpose_hook],
        )

        # Add message with note 36
        message_scheduler.add_message(0, {"track": "kick", "note": 36})

        await executor.execute_step(0, 120.0)

        # Note should be transposed to 48
        assert len(message_router.sent_messages) == 1
        assert message_router.sent_messages[0]["note"] == 48

    @pytest.mark.asyncio
    async def test_apply_multiple_hooks(
        self, message_scheduler, message_router, message_filter, timeline_provider
    ):
        """Multiple hooks should be applied in order."""

        def add_12(messages, bpm, step):
            return [{**m, "note": m["note"] + 12} if "note" in m else m for m in messages]

        def multiply_2(messages, bpm, step):
            return [{**m, "note": m["note"] * 2} if "note" in m else m for m in messages]

        executor = StepExecutor(
            message_scheduler=message_scheduler,
            message_router=message_router,
            state_publisher=MockStatePublisher(),
            message_filter=message_filter,
            timeline_provider=timeline_provider,
            session_loaded_check=lambda: True,
            get_tracks_info=lambda: [],
            before_send_hooks=[add_12, multiply_2],
        )

        # Add message with note 36
        message_scheduler.add_message(0, {"track": "kick", "note": 36})

        await executor.execute_step(0, 120.0)

        # (36 + 12) * 2 = 96
        assert message_router.sent_messages[0]["note"] == 96


class TestPeriodicUpdates:
    """Test periodic state updates."""

    @pytest.mark.asyncio
    async def test_position_update_on_beat(self, executor, state_publisher):
        """Position should be published every beat (4 steps)."""
        # Execute steps 0-7
        for step in range(8):
            await executor.execute_step(step, 120.0)

        # Position should be published at steps 0 and 4
        assert len(state_publisher.positions) == 2

    @pytest.mark.asyncio
    async def test_position_update_interval_bar(
        self, message_scheduler, message_router, state_publisher, message_filter, timeline_provider
    ):
        """Position interval 'bar' should publish every 16 steps."""
        executor = StepExecutor(
            message_scheduler=message_scheduler,
            message_router=message_router,
            state_publisher=state_publisher,
            message_filter=message_filter,
            timeline_provider=timeline_provider,
            session_loaded_check=lambda: True,
            get_tracks_info=lambda: [],
            position_update_interval="bar",
        )

        # Execute steps 0-15
        for step in range(16):
            await executor.execute_step(step, 120.0)

        # Position should be published only at step 0
        assert len(state_publisher.positions) == 1

    @pytest.mark.asyncio
    async def test_tracks_update_on_bar(self, executor, state_publisher):
        """Tracks should be published every bar (16 steps)."""
        # Execute steps 0-15
        for step in range(16):
            await executor.execute_step(step, 120.0)

        # Tracks should be published only at step 0
        assert len(state_publisher.tracks) == 1

    @pytest.mark.asyncio
    async def test_tracks_update_content(self, executor, state_publisher, get_tracks_info):
        """Tracks update should contain correct info."""
        await executor.execute_step(0, 120.0)

        assert len(state_publisher.tracks) == 1
        assert state_publisher.tracks[0] == [{"track": "kick", "muted": False}]


class TestSessionLoadedCheck:
    """Test session loaded gate."""

    @pytest.mark.asyncio
    async def test_no_messages_when_session_not_loaded(
        self, message_scheduler, message_router, state_publisher, message_filter, timeline_provider
    ):
        """Messages should not be sent if session not loaded."""
        executor = StepExecutor(
            message_scheduler=message_scheduler,
            message_router=message_router,
            state_publisher=state_publisher,
            message_filter=message_filter,
            timeline_provider=timeline_provider,
            session_loaded_check=lambda: False,  # Not loaded
            get_tracks_info=lambda: [],
        )

        # Add message
        message_scheduler.add_message(0, {"track": "kick", "note": 36})

        await executor.execute_step(0, 120.0)

        # No messages should be sent
        assert len(message_router.sent_messages) == 0


class TestErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_error_in_hook_sends_error(
        self, message_scheduler, message_router, state_publisher, message_filter, timeline_provider
    ):
        """Error in hook should send error notification."""

        def failing_hook(messages, bpm, step):
            raise ValueError("Hook error")

        executor = StepExecutor(
            message_scheduler=message_scheduler,
            message_router=message_router,
            state_publisher=state_publisher,
            message_filter=message_filter,
            timeline_provider=timeline_provider,
            session_loaded_check=lambda: True,
            get_tracks_info=lambda: [],
            before_send_hooks=[failing_hook],
        )

        # Add message
        message_scheduler.add_message(0, {"track": "kick", "note": 36})

        await executor.execute_step(0, 120.0)

        # Error should be sent
        assert len(state_publisher.errors) == 1
        assert state_publisher.errors[0]["code"] == "STEP_ERROR"

    @pytest.mark.asyncio
    async def test_error_does_not_crash_executor(
        self, message_scheduler, message_router, state_publisher, message_filter, timeline_provider
    ):
        """Error should not crash executor."""

        def failing_hook(messages, bpm, step):
            raise ValueError("Hook error")

        executor = StepExecutor(
            message_scheduler=message_scheduler,
            message_router=message_router,
            state_publisher=state_publisher,
            message_filter=message_filter,
            timeline_provider=timeline_provider,
            session_loaded_check=lambda: True,
            get_tracks_info=lambda: [],
            before_send_hooks=[failing_hook],
        )

        # Add message
        message_scheduler.add_message(0, {"track": "kick", "note": 36})

        # Should not raise
        await executor.execute_step(0, 120.0)
        await executor.execute_step(1, 120.0)  # Can continue


class TestTimelineLookahead:
    """Test timeline lookahead application."""

    @pytest.mark.asyncio
    async def test_timeline_lookahead_skipped_when_no_timeline(
        self, executor, timeline_provider
    ):
        """Lookahead should be skipped when no timeline."""
        timeline_provider._timeline = None

        # Should not raise
        await executor.execute_step(0, 120.0)

    @pytest.mark.asyncio
    async def test_timeline_lookahead_with_timeline(
        self, executor, timeline_provider
    ):
        """Lookahead should be applied when timeline exists."""
        # Create a mock timeline object
        timeline_provider._timeline = object()  # Non-None timeline
        timeline_provider._global_step = 100

        # Should not raise (actual timeline loading tested in integration tests)
        await executor.execute_step(0, 120.0)
