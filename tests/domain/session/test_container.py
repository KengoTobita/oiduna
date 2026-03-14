"""Tests for SessionContainer."""

import pytest
from typing import Any
from oiduna.domain.models import OscDestinationConfig
from oiduna.domain.session.container import SessionContainer


class TestSessionContainer:
    """Test SessionContainer integration."""

    def test_container_initialization(self) -> None:
        """Test that container initializes all services."""
        container = SessionContainer()

        assert container.session is not None
        assert container.clients is not None
        assert container.destinations is not None
        assert container.environment is not None
        assert container.tracks is not None
        assert container.patterns is not None
        assert container.timeline is not None

    def test_client_service_integration(self) -> None:
        """Test client service through container."""
        container = SessionContainer()

        # Create client
        client = container.clients.create("c1", "Alice", "mars")
        assert client.client_id == "c1"
        assert client.client_name == "Alice"

        # Get client
        retrieved = container.clients.get("c1")
        assert retrieved is not None
        assert retrieved.client_id == "c1"

    def test_track_service_integration(self) -> None:
        """Test track service through container."""
        container = SessionContainer()

        # Setup prerequisites
        container.destination_repo.save(
            OscDestinationConfig(
                id="sd", type="osc", host="127.0.0.1", port=57120, address="/dirt/play"
            )
        )
        container.clients.create("c1", "Alice")

        # Create track
        track = container.tracks.create("kick", "sd", "c1")
        assert track.track_name == "kick"
        assert track.destination_id == "sd"
        assert track.client_id == "c1"

        # Get track
        retrieved = container.tracks.get(track.track_id)
        assert retrieved is not None
        assert retrieved.track_id == track.track_id

    def test_pattern_service_integration(self) -> None:
        """Test pattern service through container."""
        container = SessionContainer()

        # Setup prerequisites
        container.destination_repo.save(
            OscDestinationConfig(
                id="sd", type="osc", host="127.0.0.1", port=57120, address="/dirt/play"
            )
        )
        container.clients.create("c1", "Alice")
        track = container.tracks.create("kick", "sd", "c1")

        # Create pattern
        pattern = container.patterns.create(track.track_id, "main", "c1")
        assert pattern.pattern_name == "main"
        assert pattern.track_id == track.track_id

        # Get pattern
        retrieved = container.patterns.get_by_id(pattern.pattern_id)
        assert retrieved is not None
        assert retrieved.pattern_id == pattern.pattern_id

    def test_environment_service_integration(self) -> None:
        """Test environment service through container."""
        container = SessionContainer()

        # Update environment
        updated = container.environment.update(bpm=140.0, metadata={"key": "Am"})
        assert updated["bpm"] == 140.0
        assert updated["metadata"] == {"key": "Am"}

        # Verify in session
        assert container.session.environment.bpm == 140.0
        assert container.session.environment.metadata == {"key": "Am"}

    def test_timeline_service_integration(self) -> None:
        """Test timeline service through container."""
        from oiduna.domain.schedule.models import LoopSchedule

        container = SessionContainer()

        # Cue a change
        batch = LoopSchedule(entries=())
        success, msg, change_id = container.timeline.cue_change(
            batch=batch,
            target_global_step=100,
            client_id="c1",
            client_name="Alice",
            description="Test",
            current_global_step=50,
        )

        assert success is True
        assert change_id is not None

        # Get change
        change = container.timeline.get_change(change_id)
        assert change is not None
        assert change.client_id == "c1"

    def test_reset_clears_session(self) -> None:
        """Test that reset clears all data."""
        container = SessionContainer()

        # Create some data
        container.destination_repo.save(
            OscDestinationConfig(
                id="sd", type="osc", host="127.0.0.1", port=57120, address="/dirt/play"
            )
        )
        container.clients.create("c1", "Alice")
        track = container.tracks.create("kick", "sd", "c1")
        container.patterns.create(track.track_id, "main", "c1")

        # Verify data exists
        assert len(container.session.clients) == 1
        assert len(container.session.tracks) == 1

        # Reset
        container.reset()

        # Verify data cleared
        assert len(container.session.clients) == 0
        assert len(container.session.tracks) == 0
        assert len(container.session.destinations) == 0

    def test_reset_reinitializes_services(self) -> None:
        """Test that reset reinitializes all services."""
        container = SessionContainer()

        # Create data
        container.destination_repo.save(
            OscDestinationConfig(
                id="sd", type="osc", host="127.0.0.1", port=57120, address="/dirt/play"
            )
        )
        container.clients.create("c1", "Alice")

        # Reset
        container.reset()

        # Services should still work with new session
        container.destination_repo.save(
            OscDestinationConfig(
                id="sd", type="osc", host="127.0.0.1", port=57120, address="/dirt/play"
            )
        )
        client = container.clients.create("c2", "Bob")
        assert client.client_id == "c2"

        # Old data should not exist
        assert container.clients.get("c1") is None

    def test_get_state_returns_session(self) -> None:
        """Test that get_state returns the session."""
        container = SessionContainer()

        state = container.get_state()
        assert state is container.session

    def test_cascade_delete_through_container(self) -> None:
        """Test cascade delete operations through container."""
        container = SessionContainer()

        # Setup
        container.destination_repo.save(
            OscDestinationConfig(
                id="sd", type="osc", host="127.0.0.1", port=57120, address="/dirt/play"
            )
        )
        container.clients.create("c1", "Alice")
        track = container.tracks.create("kick", "sd", "c1")
        pattern = container.patterns.create(track.track_id, "main", "c1")

        # Delete track (should cascade delete pattern)
        result = container.tracks.delete(track.track_id)
        assert result is True

        # Pattern should be gone
        assert container.patterns.get_by_id(pattern.pattern_id) is None

    def test_event_emission_through_container(self) -> None:
        """Test that events are emitted through container."""
        events: list[dict[str, Any]] = []

        class MockEventSink:
            def publish(self, event: dict[str, Any]) -> None:
                events.append(event)

        container = SessionContainer(MockEventSink())

        # Create client (should emit event)
        container.clients.create("c1", "Alice")

        assert len(events) == 1
        assert events[0]["type"] == "client_connected"
        assert events[0]["data"]["client_id"] == "c1"
