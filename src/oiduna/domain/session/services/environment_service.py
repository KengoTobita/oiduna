"""Environment service for environment business logic."""

from typing import Any, Optional
from oiduna.domain.models import Environment
from oiduna.domain.session.types import SessionChangePublisher
from oiduna.domain.session.repositories.environment_repository import (
    EnvironmentRepository,
)
from .base import BaseService


class EnvironmentService(BaseService):
    """
    Service for environment business logic.

    Handles validation and event emission for environment updates.
    """

    def __init__(
        self,
        environment_repo: EnvironmentRepository,
        change_publisher: Optional[SessionChangePublisher] = None,
    ) -> None:
        """
        Initialize the EnvironmentService.

        Args:
            environment_repo: Repository for environment data access
            change_publisher: Optional event publisher for emitting state changes
        """
        super().__init__(change_publisher)
        self.environment_repo = environment_repo

    def update(
        self,
        bpm: Optional[float] = None,
        metadata: Optional[dict[str, Any]] = None,
        position_update_interval: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Update environment settings.

        Args:
            bpm: New BPM (optional)
            metadata: Metadata to merge (optional)
            position_update_interval: Position update frequency: 'beat' or 'bar' (optional)

        Returns:
            Dictionary of updated fields

        Raises:
            ValueError: If position_update_interval is not 'beat' or 'bar'
        """
        updated_fields: dict[str, Any] = {}

        if bpm is not None:
            self.environment_repo.set("bpm", bpm)
            updated_fields["bpm"] = bpm

        if metadata is not None:
            current_metadata = self.environment_repo.get("metadata") or {}
            current_metadata.update(metadata)
            self.environment_repo.set("metadata", current_metadata)
            updated_fields["metadata"] = metadata

        if position_update_interval is not None:
            if position_update_interval not in ("beat", "bar"):
                raise ValueError("position_update_interval must be 'beat' or 'bar'")
            self.environment_repo.set(
                "position_update_interval", position_update_interval
            )
            updated_fields["position_update_interval"] = position_update_interval

        # Emit event only if something was updated
        if updated_fields:
            self._emit_change("environment_updated", updated_fields)

        return updated_fields

    def get_all(self) -> dict[str, Any]:
        """
        Get all environment settings.

        Returns:
            Dictionary of all environment settings
        """
        return self.environment_repo.get_all()
