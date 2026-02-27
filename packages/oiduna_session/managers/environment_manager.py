"""Environment manager for session environment settings."""

from typing import Any, Optional
from oiduna_models import Environment, Session
from .base import BaseManager, EventSink


class EnvironmentManager(BaseManager):
    """
    Manages session environment settings (BPM, metadata).

    Provides update operations for global session environment.
    """

    def __init__(
        self,
        session: Session,
        event_sink: Optional[EventSink] = None,
    ) -> None:
        """
        Initialize the EnvironmentManager.

        Args:
            session: The session object to manage
            event_sink: Optional event sink for emitting state changes
        """
        super().__init__(session, event_sink)

    def update(
        self,
        bpm: Optional[float] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Environment:
        """
        Update environment settings.

        Args:
            bpm: New BPM (optional)
            metadata: Metadata to merge (optional)

        Returns:
            Updated Environment
        """
        updated_fields: dict[str, Any] = {}
        if bpm is not None:
            self.session.environment.bpm = bpm
            updated_fields["bpm"] = bpm
        if metadata is not None:
            self.session.environment.metadata.update(metadata)
            updated_fields["metadata"] = metadata

        # Emit event
        if updated_fields:
            self._emit_event("environment_updated", updated_fields)

        return self.session.environment
