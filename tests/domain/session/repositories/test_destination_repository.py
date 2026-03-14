"""Tests for DestinationRepository."""

import pytest
from oiduna.domain.models import Session, OscDestinationConfig, MidiDestinationConfig
from oiduna.domain.session.repositories import DestinationRepository


class TestDestinationRepository:
    """Test DestinationRepository data access operations."""

    def test_save_and_get_osc_destination(self, session: Session) -> None:
        """Test saving and retrieving an OSC destination."""
        repo = DestinationRepository(session)
        dest = OscDestinationConfig(
            id="superdirt",
            type="osc",
            host="127.0.0.1",
            port=57120,
            address="/dirt/play",
        )

        repo.save(dest)
        retrieved = repo.get("superdirt")

        assert retrieved is not None
        assert retrieved.id == "superdirt"
        assert retrieved.type == "osc"
        assert retrieved.port == 57120

    def test_save_and_get_midi_destination(self, session: Session) -> None:
        """Test saving and retrieving a MIDI destination."""
        repo = DestinationRepository(session)
        dest = MidiDestinationConfig(
            id="volca",
            type="midi",
            port_name="USB MIDI 1",
            default_channel=0,
        )

        repo.save(dest)
        retrieved = repo.get("volca")

        assert retrieved is not None
        assert retrieved.id == "volca"
        assert retrieved.type == "midi"

    def test_get_nonexistent(self, session: Session) -> None:
        """Test getting a nonexistent destination returns None."""
        repo = DestinationRepository(session)
        assert repo.get("nonexistent") is None

    def test_exists(self, session: Session) -> None:
        """Test checking destination existence."""
        repo = DestinationRepository(session)
        dest = OscDestinationConfig(
            id="superdirt",
            type="osc",
            port=57120,
            address="/dirt/play",
        )

        assert not repo.exists("superdirt")
        repo.save(dest)
        assert repo.exists("superdirt")

    def test_list_all_empty(self, session: Session) -> None:
        """Test listing destinations when none exist."""
        repo = DestinationRepository(session)
        assert repo.list_all() == []

    def test_list_all_multiple(self, session: Session) -> None:
        """Test listing multiple destinations."""
        repo = DestinationRepository(session)

        dest1 = OscDestinationConfig(
            id="superdirt", type="osc", port=57120, address="/dirt/play"
        )
        dest2 = MidiDestinationConfig(
            id="volca", type="midi", port_name="USB MIDI 1"
        )

        repo.save(dest1)
        repo.save(dest2)

        all_dests = repo.list_all()
        assert len(all_dests) == 2
        assert set(d.id for d in all_dests) == {"superdirt", "volca"}

    def test_delete_existing(self, session: Session) -> None:
        """Test deleting an existing destination."""
        repo = DestinationRepository(session)
        dest = OscDestinationConfig(
            id="superdirt", type="osc", port=57120, address="/dirt/play"
        )

        repo.save(dest)
        assert repo.exists("superdirt")

        result = repo.delete("superdirt")
        assert result is True
        assert not repo.exists("superdirt")

    def test_delete_nonexistent(self, session: Session) -> None:
        """Test deleting a nonexistent destination returns False."""
        repo = DestinationRepository(session)
        result = repo.delete("nonexistent")
        assert result is False

    def test_save_overwrites(self, session: Session) -> None:
        """Test that save overwrites existing destination."""
        repo = DestinationRepository(session)

        dest1 = OscDestinationConfig(
            id="superdirt", type="osc", port=57120, address="/dirt/play"
        )
        repo.save(dest1)

        dest2 = OscDestinationConfig(
            id="superdirt", type="osc", port=57121, address="/dirt/play"
        )
        repo.save(dest2)

        retrieved = repo.get("superdirt")
        assert retrieved is not None
        assert retrieved.port == 57121
