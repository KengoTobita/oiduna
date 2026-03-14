"""Tests for TimelineRepository."""

import pytest
from oiduna.domain.timeline import CuedChange
from oiduna.domain.schedule.models import LoopSchedule
from oiduna.domain.session.repositories import TimelineRepository


class TestTimelineRepository:
    """Test TimelineRepository data access operations."""

    def test_add_and_get_change(self) -> None:
        """Test adding and retrieving a change."""
        repo = TimelineRepository()

        # Create a change
        batch = LoopSchedule(entries=())
        change = CuedChange(
            target_global_step=100,
            batch=batch,
            client_id="c1",
            client_name="Alice",
            description="Test change",
        )

        # Add change
        success, msg = repo.add_change(change, current_global_step=50)
        assert success is True
        assert msg == ""

        # Get change
        retrieved = repo.get_change_by_id(change.change_id)
        assert retrieved is not None
        assert retrieved.change_id == change.change_id
        assert retrieved.client_id == "c1"

    def test_add_change_past_step_fails(self) -> None:
        """Test that adding change to past step fails."""
        repo = TimelineRepository()

        batch = LoopSchedule(entries=())
        change = CuedChange(
            target_global_step=50,
            batch=batch,
            client_id="c1",
            client_name="Alice",
            description="Test",
        )

        # Try to add change in the past
        success, msg = repo.add_change(change, current_global_step=100)
        assert success is False
        assert "must be >" in msg

    def test_cancel_change(self) -> None:
        """Test cancelling a change."""
        repo = TimelineRepository()

        batch = LoopSchedule(entries=())
        change = CuedChange(
            target_global_step=100,
            batch=batch,
            client_id="c1",
            client_name="Alice",
            description="Test",
        )

        repo.add_change(change, current_global_step=50)

        # Cancel
        success, msg = repo.cancel_change(change.change_id)
        assert success is True

        # Verify it's gone
        assert repo.get_change_by_id(change.change_id) is None

    def test_cancel_nonexistent_change(self) -> None:
        """Test cancelling nonexistent change fails."""
        repo = TimelineRepository()

        success, msg = repo.cancel_change("nonexistent")
        assert success is False
        assert "not found" in msg

    def test_update_change(self) -> None:
        """Test updating a change."""
        repo = TimelineRepository()

        batch = LoopSchedule(entries=())
        change = CuedChange(
            target_global_step=100,
            batch=batch,
            client_id="c1",
            client_name="Alice",
            description="Original",
        )

        repo.add_change(change, current_global_step=50)

        # Update
        new_change = CuedChange(
            change_id=change.change_id,
            target_global_step=150,
            batch=batch,
            client_id="c1",
            client_name="Alice",
            description="Updated",
            cued_at=change.cued_at,
        )

        success, msg = repo.update_change(
            change.change_id, new_change, current_global_step=50
        )
        assert success is True

        # Verify update
        retrieved = repo.get_change_by_id(change.change_id)
        assert retrieved is not None
        assert retrieved.description == "Updated"
        assert retrieved.target_global_step == 150

    def test_get_all_upcoming(self) -> None:
        """Test getting all upcoming changes."""
        repo = TimelineRepository()

        batch = LoopSchedule(entries=())

        # Add multiple changes
        change1 = CuedChange(
            target_global_step=100,
            batch=batch,
            client_id="c1",
            client_name="Alice",
            description="Change 1",
        )
        change2 = CuedChange(
            target_global_step=150,
            batch=batch,
            client_id="c1",
            client_name="Alice",
            description="Change 2",
        )

        repo.add_change(change1, current_global_step=50)
        repo.add_change(change2, current_global_step=50)

        # Get upcoming
        upcoming = repo.get_all_upcoming(current_global_step=75, limit=100)
        assert len(upcoming) == 2

        # Should not include past changes
        upcoming = repo.get_all_upcoming(current_global_step=125, limit=100)
        assert len(upcoming) == 1
        assert upcoming[0].change_id == change2.change_id
