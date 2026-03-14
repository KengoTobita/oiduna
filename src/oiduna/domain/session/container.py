"""SessionContainer - Repository/Service container."""

from typing import Optional
from oiduna.domain.models import Session
from .types import SessionChangePublisher

# Import repositories
from .repositories import (
    ClientRepository,
    DestinationRepository,
    EnvironmentRepository,
    TrackRepository,
    PatternRepository,
    TimelineRepository,
)

# Import services
from .services import (
    ClientService,
    DestinationService,
    EnvironmentService,
    TrackService,
    PatternService,
    TimelineService,
)


class SessionContainer:
    """
    Repository/Service container.

    Exposes services that handle business logic and coordinate repositories.
    API accesses them directly like container.clients.create().

    Architecture:
    - Repository layer: Pure data access (session.tracks, session.clients, etc.)
    - Service layer: Business logic, validation, event emission

    Example:
        >>> container = SessionContainer()
        >>> client = container.clients.create("c1", "Alice", "mars")
        >>> track = container.tracks.create("kick", "sd", "c1")
        >>> pattern = container.patterns.create(track.track_id, "main", "c1")
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

        # Initialize Repository layer
        self.client_repo = ClientRepository(self.session)
        self.destination_repo = DestinationRepository(self.session)
        self.environment_repo = EnvironmentRepository(self.session)
        self.track_repo = TrackRepository(self.session)
        self.pattern_repo = PatternRepository(self.session)
        self.timeline_repo = TimelineRepository(self.session)

        # Initialize Service layer (APIs use these)
        self.clients = ClientService(
            self.client_repo,
            self.track_repo,
            self.pattern_repo,
            change_publisher,
        )
        self.destinations = DestinationService(
            self.destination_repo,
            self.track_repo,
            change_publisher,
        )
        self.environment = EnvironmentService(
            self.environment_repo,
            change_publisher,
        )
        self.tracks = TrackService(
            self.track_repo,
            self.destination_repo,
            self.client_repo,
            self.session._id_generator,
            change_publisher,
        )
        self.patterns = PatternService(
            self.pattern_repo,
            self.track_repo,
            self.client_repo,
            self.session._id_generator,
            change_publisher,
        )
        self.timeline = TimelineService(
            self.timeline_repo,
            change_publisher,
        )

    def reset(self) -> None:
        """Reset session to empty state (admin operation)."""
        self.session = Session()
        # New _id_generator is automatically created when Session is created

        # Reinitialize Repository layer
        self.client_repo = ClientRepository(self.session)
        self.destination_repo = DestinationRepository(self.session)
        self.environment_repo = EnvironmentRepository(self.session)
        self.track_repo = TrackRepository(self.session)
        self.pattern_repo = PatternRepository(self.session)
        self.timeline_repo = TimelineRepository(self.session)

        # Reinitialize Service layer with new repositories
        self.clients = ClientService(
            self.client_repo,
            self.track_repo,
            self.pattern_repo,
            self.change_publisher,
        )
        self.destinations = DestinationService(
            self.destination_repo,
            self.track_repo,
            self.change_publisher,
        )
        self.environment = EnvironmentService(
            self.environment_repo,
            self.change_publisher,
        )
        self.tracks = TrackService(
            self.track_repo,
            self.destination_repo,
            self.client_repo,
            self.session._id_generator,
            self.change_publisher,
        )
        self.patterns = PatternService(
            self.pattern_repo,
            self.track_repo,
            self.client_repo,
            self.session._id_generator,
            self.change_publisher,
        )
        self.timeline = TimelineService(
            self.timeline_repo,
            self.change_publisher,
        )

    def get_state(self) -> Session:
        """Get complete session state."""
        return self.session
