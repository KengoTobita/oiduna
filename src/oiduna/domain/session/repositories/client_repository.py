"""Client repository for session client data access."""

from typing import Optional
from oiduna.domain.models import Session, ClientInfo
from .base import BaseRepository


class ClientRepository(BaseRepository):
    """
    Repository for client CRUD operations.

    Provides direct access to session.clients dictionary.
    No validation or event emission - pure data access only.
    """

    def save(self, client: ClientInfo) -> None:
        """
        Save a client to the session.

        Args:
            client: ClientInfo to save
        """
        self.session.clients[client.client_id] = client

    def get(self, client_id: str) -> Optional[ClientInfo]:
        """
        Get client by ID.

        Args:
            client_id: ID of the client

        Returns:
            ClientInfo if found, None otherwise
        """
        return self.session.clients.get(client_id)

    def exists(self, client_id: str) -> bool:
        """
        Check if client exists.

        Args:
            client_id: ID of the client

        Returns:
            True if client exists, False otherwise
        """
        return client_id in self.session.clients

    def list_all(self) -> list[ClientInfo]:
        """
        List all clients.

        Returns:
            List of all ClientInfo objects
        """
        return list(self.session.clients.values())

    def delete(self, client_id: str) -> bool:
        """
        Delete a client.

        Args:
            client_id: ID of the client to delete

        Returns:
            True if deleted, False if not found
        """
        if client_id in self.session.clients:
            del self.session.clients[client_id]
            return True
        return False
