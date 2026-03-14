"""Tests for TrackRepository."""

import pytest
from oiduna.domain.models import Session, Track
from oiduna.domain.session.repositories import TrackRepository


class TestTrackRepository:
    """Test TrackRepository data access operations."""

    def test_save_and_get(self, session: Session) -> None:
        """Test saving and retrieving a track."""
        repo = TrackRepository(session)
        track = Track(
            track_id="0001",
            track_name="kick",
            destination_id="superdirt",
            client_id="client_001",
            base_params={"sound": "bd"},
        )

        repo.save(track)
        retrieved = repo.get("0001")

        assert retrieved is not None
        assert retrieved.track_id == "0001"
        assert retrieved.track_name == "kick"
        assert retrieved.destination_id == "superdirt"
        assert retrieved.client_id == "client_001"
        assert retrieved.base_params == {"sound": "bd"}

    def test_get_nonexistent(self, session: Session) -> None:
        """Test getting a nonexistent track returns None."""
        repo = TrackRepository(session)
        assert repo.get("9999") is None

    def test_exists(self, session: Session) -> None:
        """Test checking track existence."""
        repo = TrackRepository(session)
        track = Track(
            track_id="0001",
            track_name="kick",
            destination_id="sd",
            client_id="c1",
        )

        assert not repo.exists("0001")
        repo.save(track)
        assert repo.exists("0001")

    def test_list_all_empty(self, session: Session) -> None:
        """Test listing tracks when none exist."""
        repo = TrackRepository(session)
        assert repo.list_all() == []

    def test_list_all_multiple(self, session: Session) -> None:
        """Test listing multiple tracks."""
        repo = TrackRepository(session)

        tracks = [
            Track(
                track_id=f"000{i}",
                track_name=f"track_{i}",
                destination_id="sd",
                client_id="c1",
            )
            for i in range(1, 4)
        ]

        for track in tracks:
            repo.save(track)

        all_tracks = repo.list_all()
        assert len(all_tracks) == 3
        assert set(t.track_id for t in all_tracks) == {"0001", "0002", "0003"}

    def test_delete_existing(self, session: Session) -> None:
        """Test deleting an existing track."""
        repo = TrackRepository(session)
        track = Track(
            track_id="0001",
            track_name="kick",
            destination_id="sd",
            client_id="c1",
        )

        repo.save(track)
        assert repo.exists("0001")

        result = repo.delete("0001")
        assert result is True
        assert not repo.exists("0001")

    def test_delete_nonexistent(self, session: Session) -> None:
        """Test deleting a nonexistent track returns False."""
        repo = TrackRepository(session)
        result = repo.delete("9999")
        assert result is False

    def test_save_overwrites(self, session: Session) -> None:
        """Test that save overwrites existing track."""
        repo = TrackRepository(session)

        track1 = Track(
            track_id="0001",
            track_name="kick",
            destination_id="sd",
            client_id="c1",
        )
        repo.save(track1)

        track2 = Track(
            track_id="0001",
            track_name="snare",
            destination_id="sd",
            client_id="c1",
        )
        repo.save(track2)

        retrieved = repo.get("0001")
        assert retrieved is not None
        assert retrieved.track_name == "snare"

    def test_delete_cascade_removes_patterns(self, session: Session) -> None:
        """Test that deleting a track also removes its patterns."""
        from oiduna.domain.models import Pattern

        repo = TrackRepository(session)

        # Create track with patterns
        track = Track(
            track_id="0001",
            track_name="kick",
            destination_id="sd",
            client_id="c1",
            patterns={
                "0a1f": Pattern(
                    pattern_id="0a1f",
                    track_id="0001",
                    pattern_name="main",
                    client_id="c1",
                ),
                "0b2e": Pattern(
                    pattern_id="0b2e",
                    track_id="0001",
                    pattern_name="fill",
                    client_id="c1",
                ),
            },
        )
        repo.save(track)

        # Delete track
        result = repo.delete("0001")
        assert result is True

        # Track and patterns should be gone
        assert repo.get("0001") is None
