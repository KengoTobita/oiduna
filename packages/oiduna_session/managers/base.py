"""Base manager class for all session managers."""

from typing import Any, Optional, Protocol
from oiduna_models import Session


class SessionChangePublisher(Protocol):
    """
    Protocol for publishing session CRUD change notifications.

    Publishes session-layer CRUD changes (track_created, pattern_updated, etc.)
    to connected clients via SSE endpoint for real-time notification.

    This is distinct from:
        - PatternEvent: Musical timing events in Pattern domain model
        - StateProducer: Loop layer state updates (position, status)

    Implementations:
        - InProcessStateProducer: In-process queue-based implementation

    Example change events:
        - client_connected, client_disconnected
        - track_created, track_updated, track_deleted
        - pattern_created, pattern_updated, pattern_archived
        - environment_updated
    """

    def publish(self, change: dict[str, Any]) -> None:
        """
        Publish a session change notification to all connected clients.

        Args:
            change: Change dictionary with 'type' and 'data' keys
                Example: {"type": "track_created", "data": {...}}
        """
        ...


class BaseManager:
    """
    Base class for all session managers.

    Provides common functionality for event emission and session access.
    All specialized managers should inherit from this class.
    """

    def __init__(
        self,
        session: Session,
        change_publisher: Optional[SessionChangePublisher] = None,
    ) -> None:
        """
        Initialize the base manager.

        Args:
            session: The session object to manage
            change_publisher: Optional session change publisher for emitting CRUD change notifications.
                Accepts SessionChangePublisher protocol.
        """
        self.session = session
        self.change_publisher = change_publisher

    def _emit_change(self, change_type: str, data: dict[str, Any]) -> None:
        """
        Emit a session change notification if change_publisher is configured.

        Args:
            change_type: Type of the change (e.g., "client_created", "track_updated")
            data: Change data dictionary
        """
        if self.change_publisher:
            try:
                self.change_publisher.publish({"type": change_type, "data": data})
            except Exception:
                # Don't fail operations if change emission fails
                pass
