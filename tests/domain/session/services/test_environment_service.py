"""Tests for EnvironmentService."""

import pytest
from typing import Any
from oiduna.domain.models import Session
from oiduna.domain.session.repositories import EnvironmentRepository
from oiduna.domain.session.services import EnvironmentService


class TestEnvironmentService:
    """Test EnvironmentService business logic operations."""

    def test_update_bpm(
        self, session: Session, mock_event_sink: tuple[Any, list[dict[str, Any]]]
    ) -> None:
        """Test updating BPM."""
        sink, events = mock_event_sink
        env_repo = EnvironmentRepository(session)
        service = EnvironmentService(env_repo, sink)

        updated = service.update(bpm=140.0)

        assert updated == {"bpm": 140.0}
        assert session.environment.bpm == 140.0

        # Verify event emission
        assert len(events) == 1
        assert events[0]["type"] == "environment_updated"
        assert events[0]["data"]["bpm"] == 140.0

    def test_update_metadata(
        self, session: Session, mock_event_sink: tuple[Any, list[dict[str, Any]]]
    ) -> None:
        """Test updating metadata."""
        sink, events = mock_event_sink
        env_repo = EnvironmentRepository(session)
        service = EnvironmentService(env_repo, sink)

        metadata = {"key": "Am", "scale": "minor"}
        updated = service.update(metadata=metadata)

        assert updated == {"metadata": metadata}
        assert session.environment.metadata == metadata

        # Verify event emission
        assert len(events) == 1
        assert events[0]["type"] == "environment_updated"
        assert events[0]["data"]["metadata"] == metadata

    def test_update_metadata_merge(self, session: Session) -> None:
        """Test that metadata updates are merged, not replaced."""
        env_repo = EnvironmentRepository(session)
        service = EnvironmentService(env_repo)

        # Set initial metadata
        service.update(metadata={"key": "C", "tempo": "fast"})

        # Update with additional metadata
        service.update(metadata={"scale": "major"})

        # Should merge, not replace
        assert session.environment.metadata == {
            "key": "C",
            "tempo": "fast",
            "scale": "major",
        }

    def test_update_position_update_interval(
        self, session: Session, mock_event_sink: tuple[Any, list[dict[str, Any]]]
    ) -> None:
        """Test updating position_update_interval."""
        sink, events = mock_event_sink
        env_repo = EnvironmentRepository(session)
        service = EnvironmentService(env_repo, sink)

        updated = service.update(position_update_interval="bar")

        assert updated == {"position_update_interval": "bar"}
        assert session.environment.position_update_interval == "bar"

        # Verify event emission
        assert len(events) == 1
        assert events[0]["type"] == "environment_updated"
        assert events[0]["data"]["position_update_interval"] == "bar"

    def test_update_position_update_interval_invalid_raises(
        self, session: Session
    ) -> None:
        """Test that invalid position_update_interval raises ValueError."""
        env_repo = EnvironmentRepository(session)
        service = EnvironmentService(env_repo)

        with pytest.raises(
            ValueError, match="position_update_interval must be 'beat' or 'bar'"
        ):
            service.update(position_update_interval="invalid")

    def test_update_multiple_fields(
        self, session: Session, mock_event_sink: tuple[Any, list[dict[str, Any]]]
    ) -> None:
        """Test updating multiple fields at once."""
        sink, events = mock_event_sink
        env_repo = EnvironmentRepository(session)
        service = EnvironmentService(env_repo, sink)

        updated = service.update(
            bpm=150.0,
            metadata={"key": "G"},
            position_update_interval="bar",
        )

        assert updated == {
            "bpm": 150.0,
            "metadata": {"key": "G"},
            "position_update_interval": "bar",
        }
        assert session.environment.bpm == 150.0
        assert session.environment.metadata == {"key": "G"}
        assert session.environment.position_update_interval == "bar"

        # Verify event emission (should be single event with all changes)
        assert len(events) == 1
        assert events[0]["type"] == "environment_updated"
        assert events[0]["data"]["bpm"] == 150.0
        assert events[0]["data"]["metadata"] == {"key": "G"}

    def test_update_no_fields_no_event(
        self, session: Session, mock_event_sink: tuple[Any, list[dict[str, Any]]]
    ) -> None:
        """Test that no event is emitted if nothing is updated."""
        sink, events = mock_event_sink
        env_repo = EnvironmentRepository(session)
        service = EnvironmentService(env_repo, sink)

        updated = service.update()

        assert updated == {}
        assert len(events) == 0

    def test_get_all(self, session: Session) -> None:
        """Test getting all environment settings."""
        env_repo = EnvironmentRepository(session)
        service = EnvironmentService(env_repo)

        # Set some values
        service.update(bpm=140.0, metadata={"key": "Am"})

        # Get all
        all_settings = service.get_all()

        assert "bpm" in all_settings
        assert all_settings["bpm"] == 140.0
        assert "metadata" in all_settings
        assert all_settings["metadata"] == {"key": "Am"}

    def test_no_event_emission_when_no_publisher(self, session: Session) -> None:
        """Test that operations work without event publisher."""
        env_repo = EnvironmentRepository(session)
        service = EnvironmentService(env_repo, None)

        updated = service.update(bpm=140.0)

        assert updated == {"bpm": 140.0}
        assert session.environment.bpm == 140.0
