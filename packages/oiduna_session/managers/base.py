"""Base manager class for all session managers."""

from typing import Any, Optional, Protocol
from oiduna_models import Session


class SessionEventPublisher(Protocol):
    """
    Protocol for publishing session CRUD events.

    Publishes session-layer CRUD events (track_created, pattern_updated, etc.)
    to connected clients via SSE endpoint for real-time notification.

    This is distinct from StateProducer (Loop layer state updates like position, status).

    Implementations:
        - InProcessStateProducer: In-process queue-based implementation

    Example events:
        - client_connected, client_disconnected
        - track_created, track_updated, track_deleted
        - pattern_created, pattern_updated, pattern_archived
        - environment_updated
    """

    def publish(self, event: dict[str, Any]) -> None:
        """
        Publish a session event to all connected clients.

        Args:
            event: Event dictionary with 'type' and 'data' keys
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
        event_publisher: Optional[SessionEventPublisher] = None,
    ) -> None:
        """
        Initialize the base manager.

        Args:
            session: The session object to manage
            event_publisher: Optional session event publisher for emitting CRUD events.
                Accepts SessionEventPublisher protocol.
        """
        self.session = session
        self.event_publisher = event_publisher

    def _emit_event(self, event_type: str, data: dict[str, Any]) -> None:
        """
        Emit an SSE event if event_publisher is configured.

        Args:
            event_type: Type of the event (e.g., "client_created")
            data: Event data dictionary
        """
        if self.event_publisher:
            try:
                self.event_publisher.publish({"type": event_type, "data": data})
            except Exception:
                # Don't fail operations if event emission fails
                pass
