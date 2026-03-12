"""SessionContainer - Lightweight manager container."""

from typing import Optional
from oiduna.domain.models import Session
from .managers.base import SessionChangePublisher
from .managers.client_manager import ClientManager
from .managers.destination_manager import DestinationManager
from .managers.environment_manager import EnvironmentManager
from .managers.track_manager import TrackManager
from .managers.pattern_manager import PatternManager
from .managers.timeline_manager import TimelineManager


class SessionContainer:
    """
    Lightweight manager container.

    Exposes each manager directly without delegation layers.
    API accesses them directly like container.clients.create().

    Example:
        >>> container = SessionContainer()
        >>> client = container.clients.create("c1", "Alice", "mars")
        >>> track = container.tracks.create("t1", "kick", "sd", "c1")
        >>> pattern = container.patterns.create("t1", "p1", "main", "c1")
    """

    def __init__(self, change_publisher: Optional[SessionChangePublisher] = None) -> None:
        """
        Initialize SessionContainer.

        Args:
            change_publisher: Optional session change publisher for SSE change notifications.
                Accepts SessionChangePublisher protocol.
        """
        self.session = Session()
        self.change_publisher = change_publisher

        # Expose each manager directly (no delegation)
        # Use Session-scoped IDGenerator
        self.clients = ClientManager(self.session, change_publisher)
        self.destinations = DestinationManager(self.session, change_publisher)
        self.tracks = TrackManager(
            self.session,
            change_publisher,
            id_generator=self.session._id_generator,
            destination_manager=self.destinations,
            client_manager=self.clients,
        )
        self.patterns = PatternManager(
            self.session,
            change_publisher,
            id_generator=self.session._id_generator,
            track_manager=self.tracks,
            client_manager=self.clients,
        )
        self.environment = EnvironmentManager(self.session, change_publisher)
        self.timeline = TimelineManager(self.session, change_publisher)

    def reset(self) -> None:
        """Reset session to empty state (admin operation)."""
        self.session = Session()
        # New _id_generator is automatically created when Session is created

        # Reinitialize all managers with new session
        self.clients.session = self.session
        self.destinations.session = self.session
        self.tracks.session = self.session
        self.tracks.id_generator = self.session._id_generator
        self.patterns.session = self.session
        self.patterns.id_generator = self.session._id_generator
        self.environment.session = self.session
        self.timeline = TimelineManager(self.session, self.change_publisher)

    def get_state(self) -> Session:
        """Get complete session state."""
        return self.session
