"""Type definitions for session domain."""

from typing import Any, Protocol


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
