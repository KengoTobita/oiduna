"""Base service class for business logic operations."""

from typing import Any, Optional
from oiduna.domain.session.types import SessionChangePublisher


class BaseService:
    """
    Base class for all services.

    Services handle business logic and coordinate repositories.

    Responsibilities:
    - Business logic and validation
    - Event emission via SessionChangePublisher
    - Coordinating multiple repositories
    - Permission checks

    Services should not:
    - Directly access session.tracks, session.clients, etc.
    - Bypass repository layer
    """

    def __init__(
        self, change_publisher: Optional[SessionChangePublisher] = None
    ) -> None:
        """
        Initialize the base service.

        Args:
            change_publisher: Optional session change publisher for emitting CRUD change notifications
        """
        self.change_publisher = change_publisher

    def _emit_change(self, change_type: str, data: dict[str, Any]) -> None:
        """
        Emit a session change notification if change_publisher is configured.

        This is the same implementation as BaseManager._emit_change.

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
