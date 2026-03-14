"""Destination repository for session destination data access."""

from typing import Optional
from oiduna.domain.models import Session, DestinationConfig
from .base import BaseRepository


class DestinationRepository(BaseRepository):
    """
    Repository for destination CRUD operations.

    Provides direct access to session.destinations dictionary.
    No validation or event emission - pure data access only.
    """

    def save(self, destination: DestinationConfig) -> None:
        """Save a destination to the session."""
        self.session.destinations[destination.id] = destination

    def get(self, destination_id: str) -> Optional[DestinationConfig]:
        """Get destination by ID."""
        return self.session.destinations.get(destination_id)

    def exists(self, destination_id: str) -> bool:
        """Check if destination exists."""
        return destination_id in self.session.destinations

    def list_all(self) -> list[DestinationConfig]:
        """List all destinations."""
        return list(self.session.destinations.values())

    def delete(self, destination_id: str) -> bool:
        """Delete a destination."""
        if destination_id in self.session.destinations:
            del self.session.destinations[destination_id]
            return True
        return False
