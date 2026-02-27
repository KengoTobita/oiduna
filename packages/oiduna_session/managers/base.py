"""Base manager class for all session managers."""

from typing import Any, Optional, Protocol
from oiduna_models import Session


class EventSink(Protocol):
    """Protocol for event sinks (e.g., InProcessStateSink)."""

    def _push(self, event: dict[str, Any]) -> None:
        """Push an event to the sink."""
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
        event_sink: Optional[EventSink] = None,
    ) -> None:
        """
        Initialize the base manager.

        Args:
            session: The session object to manage
            event_sink: Optional event sink for emitting state changes
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
