"""Client service for client business logic."""

from typing import Any, Optional
from oiduna.domain.models import ClientInfo
from oiduna.domain.session.types import SessionChangePublisher
from oiduna.domain.session.repositories.client_repository import ClientRepository
from .base import BaseService


class ClientService(BaseService):
    """
    Service for client business logic.

    Handles validation, event emission, and cascade operations.
    Coordinates ClientRepository and other repositories for complex operations.
    """

    def __init__(
        self,
        client_repo: ClientRepository,
        track_repo: Any,  # TrackRepository - avoid circular import
        pattern_repo: Any,  # PatternRepository - avoid circular import
        change_publisher: Optional[SessionChangePublisher] = None,
    ) -> None:
        """
        Initialize the ClientService.

        Args:
            client_repo: Repository for client data access
            track_repo: Repository for track data access (for cascade delete)
            pattern_repo: Repository for pattern data access (for cascade delete)
            change_publisher: Optional event publisher for emitting state changes
        """
        super().__init__(change_publisher)
        self.client_repo = client_repo
        self.track_repo = track_repo
        self.pattern_repo = pattern_repo

    def create(
        self,
        client_id: str,
        client_name: str,
        distribution: str = "unknown",
        metadata: Optional[dict[str, Any]] = None,
    ) -> ClientInfo:
        """
        Create a new client.

        Args:
            client_id: Unique client identifier
            client_name: Human-readable name
            distribution: Client type (mars, web, mobile, etc.)
            metadata: Additional metadata

        Returns:
            Created ClientInfo with generated token

        Raises:
            ValueError: If client_id already exists
        """
        if self.client_repo.exists(client_id):
            raise ValueError(f"Client {client_id} already exists")

        client = ClientInfo(
            client_id=client_id,
            client_name=client_name,
            token=ClientInfo.generate_token(),
            distribution=distribution,
            metadata=metadata or {},
        )

        self.client_repo.save(client)

        # Emit event
        self._emit_change(
            "client_connected",
            {
                "client_id": client_id,
                "client_name": client_name,
                "distribution": distribution,
            },
        )

        return client

    def get(self, client_id: str) -> Optional[ClientInfo]:
        """
        Get client by ID.

        Args:
            client_id: ID of the client

        Returns:
            ClientInfo if found, None otherwise
        """
        return self.client_repo.get(client_id)

    def list_clients(self) -> list[ClientInfo]:
        """
        List all clients.

        Returns:
            List of all ClientInfo objects
        """
        return self.client_repo.list_all()

    def delete(self, client_id: str) -> bool:
        """
        Delete a client.

        Note: Does not cascade delete tracks/patterns owned by this client.
        Call delete_resources() first if cascading delete is needed.

        Args:
            client_id: ID of the client to delete

        Returns:
            True if deleted, False if not found
        """
        if not self.client_repo.exists(client_id):
            return False

        self.client_repo.delete(client_id)

        # Emit event
        self._emit_change("client_disconnected", {"client_id": client_id})

        return True

    def delete_resources(self, client_id: str) -> dict[str, int]:
        """
        Delete all resources owned by a client (tracks and their patterns).

        Args:
            client_id: ID of the client whose resources to delete

        Returns:
            Dictionary with counts: {"tracks": N, "patterns": M}
        """
        tracks_deleted = 0
        patterns_deleted = 0

        # Find and delete tracks owned by this client
        all_tracks = self.track_repo.list_all()
        track_ids_to_delete = [
            track.track_id for track in all_tracks if track.client_id == client_id
        ]

        for track_id in track_ids_to_delete:
            track = self.track_repo.get(track_id)
            if track:
                patterns_deleted += len(track.patterns)
                self.track_repo.delete(track_id)
                tracks_deleted += 1

        return {"tracks": tracks_deleted, "patterns": patterns_deleted}
