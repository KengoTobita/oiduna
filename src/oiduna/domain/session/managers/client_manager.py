"""Client manager for session client management."""

from typing import Any, Optional
from oiduna.domain.models import Session, ClientInfo
from .base import BaseManager, SessionChangePublisher


class ClientManager(BaseManager):
    """
    Manages client CRUD operations in the session.

    Provides creation, retrieval, listing, and deletion of clients.
    """

    def __init__(
        self,
        session: Session,
        event_publisher: Optional[SessionChangePublisher] = None,
    ) -> None:
        """
        Initialize the ClientManager.

        Args:
            session: The session object to manage
            event_publisher: Optional event publisher for emitting state changes
        """
        super().__init__(session, event_publisher)

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
        if client_id in self.session.clients:
            raise ValueError(f"Client {client_id} already exists")

        client = ClientInfo(
            client_id=client_id,
            client_name=client_name,
            token=ClientInfo.generate_token(),
            distribution=distribution,
            metadata=metadata or {},
        )

        self.session.clients[client_id] = client

        # Emit event
        self._emit_change("client_connected", {
            "client_id": client_id,
            "client_name": client_name,
            "distribution": distribution,
        })

        return client

    def get(self, client_id: str) -> Optional[ClientInfo]:
        """
        Get client by ID.

        Args:
            client_id: ID of the client

        Returns:
            ClientInfo if found, None otherwise
        """
        return self.session.clients.get(client_id)

    def list_clients(self) -> list[ClientInfo]:
        """
        List all clients.

        Returns:
            List of all ClientInfo objects
        """
        return list(self.session.clients.values())

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
        if client_id in self.session.clients:
            del self.session.clients[client_id]

            # Emit event
            self._emit_change("client_disconnected", {
                "client_id": client_id,
            })

            return True
        return False

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
        track_ids_to_delete = [
            track_id
            for track_id, track in self.session.tracks.items()
            if track.client_id == client_id
        ]

        for track_id in track_ids_to_delete:
            track = self.session.tracks[track_id]
            patterns_deleted += len(track.patterns)
            del self.session.tracks[track_id]
            tracks_deleted += 1

        return {"tracks": tracks_deleted, "patterns": patterns_deleted}
