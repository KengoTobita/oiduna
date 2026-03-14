"""Tests for ClientRepository."""

import pytest
from oiduna.domain.models import Session, ClientInfo
from oiduna.domain.session.repositories import ClientRepository


class TestClientRepository:
    """Test ClientRepository data access operations."""

    def test_save_and_get(self, session: Session) -> None:
        """Test saving and retrieving a client."""
        repo = ClientRepository(session)
        client = ClientInfo(
            client_id="c1",
            client_name="Alice",
            token=ClientInfo.generate_token(),
            distribution="mars",
        )

        repo.save(client)
        retrieved = repo.get("c1")

        assert retrieved is not None
        assert retrieved.client_id == "c1"
        assert retrieved.client_name == "Alice"
        assert retrieved.distribution == "mars"

    def test_get_nonexistent(self, session: Session) -> None:
        """Test getting a nonexistent client returns None."""
        repo = ClientRepository(session)
        assert repo.get("nonexistent") is None

    def test_exists(self, session: Session) -> None:
        """Test checking client existence."""
        repo = ClientRepository(session)
        client = ClientInfo(
            client_id="c1",
            client_name="Alice",
            token=ClientInfo.generate_token(),
        )

        assert not repo.exists("c1")
        repo.save(client)
        assert repo.exists("c1")

    def test_list_all_empty(self, session: Session) -> None:
        """Test listing clients when none exist."""
        repo = ClientRepository(session)
        assert repo.list_all() == []

    def test_list_all_multiple(self, session: Session) -> None:
        """Test listing multiple clients."""
        repo = ClientRepository(session)

        clients = [
            ClientInfo(
                client_id=f"c{i}",
                client_name=f"Client {i}",
                token=ClientInfo.generate_token(),
            )
            for i in range(3)
        ]

        for client in clients:
            repo.save(client)

        all_clients = repo.list_all()
        assert len(all_clients) == 3
        assert set(c.client_id for c in all_clients) == {"c0", "c1", "c2"}

    def test_delete_existing(self, session: Session) -> None:
        """Test deleting an existing client."""
        repo = ClientRepository(session)
        client = ClientInfo(
            client_id="c1",
            client_name="Alice",
            token=ClientInfo.generate_token(),
        )

        repo.save(client)
        assert repo.exists("c1")

        result = repo.delete("c1")
        assert result is True
        assert not repo.exists("c1")

    def test_delete_nonexistent(self, session: Session) -> None:
        """Test deleting a nonexistent client returns False."""
        repo = ClientRepository(session)
        result = repo.delete("nonexistent")
        assert result is False

    def test_save_overwrites(self, session: Session) -> None:
        """Test that save overwrites existing client."""
        repo = ClientRepository(session)

        client1 = ClientInfo(
            client_id="c1",
            client_name="Alice",
            token=ClientInfo.generate_token(),
        )
        repo.save(client1)

        client2 = ClientInfo(
            client_id="c1",
            client_name="Bob",
            token=ClientInfo.generate_token(),
        )
        repo.save(client2)

        retrieved = repo.get("c1")
        assert retrieved is not None
        assert retrieved.client_name == "Bob"
