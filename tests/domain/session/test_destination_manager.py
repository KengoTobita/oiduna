"""Direct tests for DestinationManager."""
import pytest
from oiduna.domain.models import Session
from oiduna.domain.session.managers.destination_manager import DestinationManager
from oiduna.domain.session import SessionContainer
from oiduna.domain.models import OscDestinationConfig


@pytest.fixture
def session():
    return Session()


@pytest.fixture
def dest_manager(session):
    return DestinationManager(session)


@pytest.fixture
def sample_destination():
    """Create a sample OSC destination config."""
    return OscDestinationConfig(
        id="superdirt",
        type="osc",
        host="127.0.0.1",
        port=57120,
        address="/dirt/play"
    )


@pytest.fixture
def container_with_client():
    """Create container with superdirt destination and client."""
    container = SessionContainer()

    # Add destination
    dest = OscDestinationConfig(
        id="superdirt",
        type="osc",
        host="127.0.0.1",
        port=57120,
        address="/dirt/play"
    )
    container.destinations.add(dest)

    # Add client
    container.clients.create("c1", "Alice", "mars")

    return container


class TestDestinationManagerAdd:
    """Test destination add operations."""

    def test_add_destination(self, dest_manager, sample_destination):
        """Test adding a destination."""
        dest_manager.add(sample_destination)
        assert "superdirt" in dest_manager.session.destinations
        retrieved = dest_manager.get("superdirt")
        assert retrieved is not None
        assert retrieved.id == "superdirt"

    def test_add_duplicate_raises(self, dest_manager, sample_destination):
        """Test that adding duplicate destination raises ValueError."""
        dest_manager.add(sample_destination)
        with pytest.raises(ValueError, match="already exists"):
            dest_manager.add(sample_destination)


class TestDestinationManagerRemove:
    """Test destination removal operations."""

    def test_remove_unused_destination_success(self, dest_manager, sample_destination):
        """Test removing unused destination succeeds."""
        dest_manager.add(sample_destination)
        result = dest_manager.remove("superdirt")
        assert result is True
        assert "superdirt" not in dest_manager.session.destinations

    def test_remove_destination_in_use_raises(self, container_with_client):
        """Test removing destination in use raises ValueError."""
        # Add track using the destination
        container_with_client.tracks.create(
            track_name="kick",
            destination_id="superdirt",
            client_id="c1"
        )

        # Try to remove destination
        with pytest.raises(ValueError, match="in use by"):
            container_with_client.destinations.remove("superdirt")

    def test_remove_error_lists_using_tracks(self, container_with_client):
        """Test error message lists tracks using destination."""
        # Add multiple tracks using the destination
        track1 = container_with_client.tracks.create(
            track_name="kick",
            destination_id="superdirt",
            client_id="c1"
        )
        track2 = container_with_client.tracks.create(
            track_name="snare",
            destination_id="superdirt",
            client_id="c1"
        )

        # Try to remove destination
        with pytest.raises(ValueError) as exc_info:
            container_with_client.destinations.remove("superdirt")

        error_msg = str(exc_info.value)
        assert track1.track_id in error_msg
        assert track2.track_id in error_msg
        assert "2 track(s)" in error_msg

    def test_remove_nonexistent_returns_false(self, dest_manager):
        """Test removing non-existent destination returns False."""
        result = dest_manager.remove("nonexistent")
        assert result is False

    def test_remove_with_helpful_error_message(self, container_with_client):
        """Test error message includes helpful instructions."""
        # Add track
        container_with_client.tracks.create(
            track_name="kick",
            destination_id="superdirt",
            client_id="c1"
        )

        # Try to remove destination
        with pytest.raises(ValueError) as exc_info:
            container_with_client.destinations.remove("superdirt")

        error_msg = str(exc_info.value)
        assert "Cannot remove destination" in error_msg
        # Check that error message contains helpful instruction
        assert any(phrase in error_msg for phrase in [
            "Delete these tracks first",
            "assign them to a different destination"
        ]), f"Error message lacks helpful instruction: {error_msg}"


class TestDestinationManagerGet:
    """Test destination retrieval operations."""

    def test_get_existing_destination(self, dest_manager, sample_destination):
        """Test getting an existing destination."""
        dest_manager.add(sample_destination)
        retrieved = dest_manager.get("superdirt")
        assert retrieved is not None
        assert retrieved.id == "superdirt"

    def test_get_nonexistent_returns_none(self, dest_manager):
        """Test getting non-existent destination returns None."""
        result = dest_manager.get("nonexistent")
        assert result is None


class TestDestinationManagerIntegration:
    """Integration tests for destination manager."""

    def test_add_remove_add_cycle(self, dest_manager, sample_destination):
        """Test adding, removing, and re-adding a destination."""
        # Add
        dest_manager.add(sample_destination)
        assert dest_manager.get("superdirt") is not None

        # Remove
        dest_manager.remove("superdirt")
        assert dest_manager.get("superdirt") is None

        # Re-add
        dest_manager.add(sample_destination)
        assert dest_manager.get("superdirt") is not None

    def test_remove_only_affects_specified_destination(self, container_with_client):
        """Test removing one destination doesn't affect others."""
        # Add second destination
        dest2 = OscDestinationConfig(
            id="midi_out",
            type="osc",
            host="127.0.0.1",
            port=57121,
            address="/midi/play"
        )
        container_with_client.destinations.add(dest2)

        # Remove one
        container_with_client.destinations.remove("superdirt")

        # Check other still exists
        assert container_with_client.destinations.get("superdirt") is None
        assert container_with_client.destinations.get("midi_out") is not None
