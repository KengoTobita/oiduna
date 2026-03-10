"""Base manager class for all session managers."""

from typing import Any, Optional, Protocol
from oiduna_models import Session


class SessionEventSink(Protocol):
    """
    Protocol for session event sinks.

    Receives session-layer CRUD events (track_created, pattern_updated, etc.)
    and forwards them to SSE endpoint for client notification.

    This is distinct from StateProducer (Loop layer state updates like position, status).

    Implementations:
        - InProcessStateSink: In-process queue-based implementation

    Example events:
        - client_connected, client_disconnected
        - track_created, track_updated, track_deleted
        - pattern_created, pattern_updated, pattern_archived
        - environment_updated
    """

    def _push(self, event: dict[str, Any]) -> None:
        """
        Push a session event to the sink.

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
        event_sink: Optional[SessionEventSink] = None,
    ) -> None:
        """
        Initialize the base manager.

        Args:
            session: The session object to manage
            event_sink: Optional session event sink for emitting CRUD events.
                Accepts SessionEventSink protocol.
        """
        self.session = session
        self.event_sink = event_sink

    def _emit_event(self, event_type: str, data: dict[str, Any]) -> None:
        """
        Emit an SSE event if event_sink is configured.

        Args:
            event_type: Type of the event (e.g., "client_created")
            data: Event data dictionary
        """
        if self.event_sink:
            try:
                self.event_sink._push({"type": event_type, "data": data})
            except Exception:
                # Don't fail operations if event emission fails
                pass
