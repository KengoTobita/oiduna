"""Base repository class for data access operations."""

from oiduna.domain.models import Session


class BaseRepository:
    """
    Base class for all repositories.

    Repositories handle CRUD operations on the Session domain model.
    They should not:
    - Emit events
    - Perform business logic validation
    - Coordinate multiple repositories

    Responsibilities:
    - Direct read/write access to session.tracks, session.clients, etc.
    - Simple queries (get, list, exists)
    """

    def __init__(self, session: Session) -> None:
        """
        Initialize the base repository.

        Args:
            session: The session object to access
        """
        self.session = session
