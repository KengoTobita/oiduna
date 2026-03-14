"""Tests for TimelineService."""

import pytest
from typing import Any
from oiduna.domain.timeline import CuedChange
from oiduna.domain.schedule.models import LoopSchedule
from oiduna.domain.session.repositories import TimelineRepository
from oiduna.domain.session.services import TimelineService
from oiduna.domain.session.services.timeline_service import TIMELINE_MIN_LOOKAHEAD


class TestTimelineService:
    """Test TimelineService business logic operations."""

    def test_cue_change(
        self, mock_event_sink: tuple[Any, list[dict[str, Any]]]
    ) -> None:
        """Test scheduling a change."""
        sink, events = mock_event_sink
        timeline_repo = TimelineRepository()
        service = TimelineService(timeline_repo, sink)

        batch = LoopSchedule(entries=())

        # Cue a change
        success, msg, change_id = service.cue_change(
            batch=batch,
            target_global_step=100,
            client_id="c1",
            client_name="Alice",
            description="Test change",
            current_global_step=50,
        )

        assert success is True
        assert msg == ""
        assert change_id is not None

        # Verify event emission
        assert len(events) == 1
        assert events[0]["type"] == "change_scheduled"
        assert events[0]["data"]["client_id"] == "c1"

    def test_cue_change_min_lookahead_validation(self) -> None:
        """Test that minimum lookahead is enforced."""
        timeline_repo = TimelineRepository()
        service = TimelineService(timeline_repo)

        batch = LoopSchedule(entries=())
        current_step = 100

        # Try to schedule too soon (less than MIN_LOOKAHEAD)
        success, msg, change_id = service.cue_change(
            batch=batch,
            target_global_step=current_step + 5,  # Only 5 steps ahead
            client_id="c1",
            client_name="Alice",
            description="Too soon",
            current_global_step=current_step,
        )

        assert success is False
        assert f"{TIMELINE_MIN_LOOKAHEAD}ステップ先" in msg
        assert change_id is None

    def test_cue_change_valid_lookahead(self) -> None:
        """Test that valid lookahead passes."""
        timeline_repo = TimelineRepository()
        service = TimelineService(timeline_repo)

        batch = LoopSchedule(entries=())
        current_step = 100

        # Schedule with valid lookahead
        success, msg, change_id = service.cue_change(
            batch=batch,
            target_global_step=current_step + TIMELINE_MIN_LOOKAHEAD,
            client_id="c1",
            client_name="Alice",
            description="Valid lookahead",
            current_global_step=current_step,
        )

        assert success is True
        assert change_id is not None

    def test_cancel_change_by_owner(
        self, mock_event_sink: tuple[Any, list[dict[str, Any]]]
    ) -> None:
        """Test cancelling a change by its owner."""
        sink, events = mock_event_sink
        timeline_repo = TimelineRepository()
        service = TimelineService(timeline_repo, sink)

        batch = LoopSchedule(entries=())

        # Create change
        success, msg, change_id = service.cue_change(
            batch=batch,
            target_global_step=100,
            client_id="c1",
            client_name="Alice",
            description="Test",
            current_global_step=50,
        )
        assert change_id is not None
        events.clear()

        # Cancel by owner
        success, msg = service.cancel_change(change_id, client_id="c1")
        assert success is True

        # Verify event emission
        assert len(events) == 1
        assert events[0]["type"] == "change_cancelled"
        assert events[0]["data"]["change_id"] == change_id

    def test_cancel_change_permission_denied(self) -> None:
        """Test that non-owner cannot cancel a change."""
        timeline_repo = TimelineRepository()
        service = TimelineService(timeline_repo)

        batch = LoopSchedule(entries=())

        # Create change by c1
        success, msg, change_id = service.cue_change(
            batch=batch,
            target_global_step=100,
            client_id="c1",
            client_name="Alice",
            description="Test",
            current_global_step=50,
        )
        assert change_id is not None

        # Try to cancel by c2
        success, msg = service.cancel_change(change_id, client_id="c2")
        assert success is False
        assert "Permission denied" in msg

    def test_cancel_nonexistent_change(self) -> None:
        """Test cancelling nonexistent change."""
        timeline_repo = TimelineRepository()
        service = TimelineService(timeline_repo)

        success, msg = service.cancel_change("nonexistent", client_id="c1")
        assert success is False
        assert "not found" in msg

    def test_update_change_by_owner(
        self, mock_event_sink: tuple[Any, list[dict[str, Any]]]
    ) -> None:
        """Test updating a change by its owner."""
        sink, events = mock_event_sink
        timeline_repo = TimelineRepository()
        service = TimelineService(timeline_repo, sink)

        batch = LoopSchedule(entries=())

        # Create change
        success, msg, change_id = service.cue_change(
            batch=batch,
            target_global_step=100,
            client_id="c1",
            client_name="Alice",
            description="Original",
            current_global_step=50,
        )
        assert change_id is not None
        events.clear()

        # Update by owner
        new_batch = LoopSchedule(entries=())
        success, msg = service.update_change(
            change_id=change_id,
            new_batch=new_batch,
            new_target_global_step=150,
            new_description="Updated",
            client_id="c1",
            current_global_step=60,
        )
        assert success is True

        # Verify update
        change = service.get_change(change_id)
        assert change is not None
        assert change.description == "Updated"
        assert change.target_global_step == 150

        # Verify event emission
        assert len(events) == 1
        assert events[0]["type"] == "change_updated"

    def test_update_change_permission_denied(self) -> None:
        """Test that non-owner cannot update a change."""
        timeline_repo = TimelineRepository()
        service = TimelineService(timeline_repo)

        batch = LoopSchedule(entries=())

        # Create change by c1
        success, msg, change_id = service.cue_change(
            batch=batch,
            target_global_step=100,
            client_id="c1",
            client_name="Alice",
            description="Test",
            current_global_step=50,
        )
        assert change_id is not None

        # Try to update by c2
        success, msg = service.update_change(
            change_id=change_id,
            new_batch=batch,
            new_target_global_step=150,
            new_description="Hacked",
            client_id="c2",
            current_global_step=60,
        )
        assert success is False
        assert "Permission denied" in msg

    def test_get_change(self) -> None:
        """Test getting a change."""
        timeline_repo = TimelineRepository()
        service = TimelineService(timeline_repo)

        batch = LoopSchedule(entries=())

        # Create change
        success, msg, change_id = service.cue_change(
            batch=batch,
            target_global_step=100,
            client_id="c1",
            client_name="Alice",
            description="Test",
            current_global_step=50,
        )
        assert change_id is not None

        # Get change
        change = service.get_change(change_id)
        assert change is not None
        assert change.change_id == change_id
        assert change.client_id == "c1"

    def test_get_nonexistent_change(self) -> None:
        """Test getting nonexistent change returns None."""
        timeline_repo = TimelineRepository()
        service = TimelineService(timeline_repo)

        change = service.get_change("nonexistent")
        assert change is None

    def test_get_all_upcoming(self) -> None:
        """Test getting all upcoming changes."""
        timeline_repo = TimelineRepository()
        service = TimelineService(timeline_repo)

        batch = LoopSchedule(entries=())

        # Create multiple changes
        service.cue_change(
            batch=batch,
            target_global_step=100,
            client_id="c1",
            client_name="Alice",
            description="Change 1",
            current_global_step=50,
        )
        service.cue_change(
            batch=batch,
            target_global_step=150,
            client_id="c1",
            client_name="Alice",
            description="Change 2",
            current_global_step=50,
        )

        # Get upcoming
        upcoming = service.get_all_upcoming(current_global_step=75, limit=100)
        assert len(upcoming) == 2

    def test_no_event_emission_when_no_publisher(self) -> None:
        """Test that operations work without event publisher."""
        timeline_repo = TimelineRepository()
        service = TimelineService(timeline_repo, None)

        batch = LoopSchedule(entries=())

        # Create change without publisher
        success, msg, change_id = service.cue_change(
            batch=batch,
            target_global_step=100,
            client_id="c1",
            client_name="Alice",
            description="Test",
            current_global_step=50,
        )
        assert success is True
        assert change_id is not None

        # Cancel without publisher
        success, msg = service.cancel_change(change_id, client_id="c1")
        assert success is True
