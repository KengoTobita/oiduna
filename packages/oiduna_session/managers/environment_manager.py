"""Environment manager for session environment settings."""

from typing import Any, Optional
from oiduna_models import Environment, Session
from .base import BaseManager, SessionChangePublisher


class EnvironmentManager(BaseManager):
    """
    Manages session environment settings (BPM, metadata).

    Provides update operations for global session environment.
    """

    def __init__(
        self,
        session: Session,
        event_publisher: Optional[SessionChangePublisher] = None,
    ) -> None:
        """
        Initialize the EnvironmentManager.

        Args:
            session: The session object to manage
            event_publisher: Optional event publisher for emitting state changes
        """
        super().__init__(session, event_publisher)

    def update(
        self,
        bpm: Optional[float] = None,
        metadata: Optional[dict[str, Any]] = None,
        position_update_interval: Optional[str] = None,
    ) -> Environment:
        """
        Update environment settings.

        Args:
            bpm: New BPM (optional)
            metadata: Metadata to merge (optional)
            position_update_interval: Position update frequency: 'beat' or 'bar' (optional)

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
        if position_update_interval is not None:
            if position_update_interval not in ("beat", "bar"):
                raise ValueError("position_update_interval must be 'beat' or 'bar'")
            self.session.environment.position_update_interval = position_update_interval  # type: ignore
            updated_fields["position_update_interval"] = position_update_interval

        # Emit event
        if updated_fields:
            self._emit_change("environment_updated", updated_fields)

        return self.session.environment
