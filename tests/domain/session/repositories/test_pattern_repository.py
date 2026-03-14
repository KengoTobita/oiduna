"""Tests for PatternRepository."""

import pytest
from oiduna.domain.models import Session, Track, Pattern
from oiduna.domain.session.repositories import PatternRepository


class TestPatternRepository:
    """Test PatternRepository data access operations."""

    def test_save_to_track(self, session: Session) -> None:
        """Test saving a pattern to a track."""
        repo = PatternRepository(session)

        # Create a track first
        track = Track(
            track_id="0001",
            track_name="kick",
            destination_id="sd",
            client_id="c1",
        )
        session.tracks["0001"] = track

        # Save pattern
        pattern = Pattern(
            pattern_id="0a1f",
            track_id="0001",
            pattern_name="main",
            client_id="c1",
        )
        repo.save_to_track("0001", pattern)

        # Verify
        assert "0a1f" in track.patterns
        assert track.patterns["0a1f"].pattern_name == "main"

    def test_save_to_nonexistent_track_raises(self, session: Session) -> None:
        """Test saving to nonexistent track raises ValueError."""
        repo = PatternRepository(session)

        pattern = Pattern(
            pattern_id="0a1f",
            track_id="9999",
            pattern_name="main",
            client_id="c1",
        )

        with pytest.raises(ValueError, match="Track 9999 not found"):
            repo.save_to_track("9999", pattern)

    def test_get_hierarchical(self, session: Session) -> None:
        """Test getting pattern by track_id and pattern_id."""
        repo = PatternRepository(session)

        # Setup track with pattern
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
                )
            },
        )
        session.tracks["0001"] = track

        # Get pattern
        pattern = repo.get("0001", "0a1f")
        assert pattern is not None
        assert pattern.pattern_id == "0a1f"
        assert pattern.pattern_name == "main"

    def test_get_nonexistent_track(self, session: Session) -> None:
        """Test getting pattern from nonexistent track returns None."""
        repo = PatternRepository(session)
        assert repo.get("9999", "0a1f") is None

    def test_get_nonexistent_pattern(self, session: Session) -> None:
        """Test getting nonexistent pattern returns None."""
        repo = PatternRepository(session)

        track = Track(
            track_id="0001",
            track_name="kick",
            destination_id="sd",
            client_id="c1",
        )
        session.tracks["0001"] = track

        assert repo.get("0001", "9999") is None

    def test_get_by_id(self, session: Session) -> None:
        """Test getting pattern by pattern_id only (flat API)."""
        repo = PatternRepository(session)

        # Setup multiple tracks with patterns
        track1 = Track(
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
                )
            },
        )
        track2 = Track(
            track_id="0002",
            track_name="snare",
            destination_id="sd",
            client_id="c1",
            patterns={
                "0b2e": Pattern(
                    pattern_id="0b2e",
                    track_id="0002",
                    pattern_name="fill",
                    client_id="c1",
                )
            },
        )
        session.tracks["0001"] = track1
        session.tracks["0002"] = track2

        # Get patterns by ID only
        pattern1 = repo.get_by_id("0a1f")
        assert pattern1 is not None
        assert pattern1.pattern_name == "main"
        assert pattern1.track_id == "0001"

        pattern2 = repo.get_by_id("0b2e")
        assert pattern2 is not None
        assert pattern2.pattern_name == "fill"
        assert pattern2.track_id == "0002"

    def test_get_by_id_nonexistent(self, session: Session) -> None:
        """Test getting nonexistent pattern by ID returns None."""
        repo = PatternRepository(session)
        assert repo.get_by_id("9999") is None

    def test_list_in_track(self, session: Session) -> None:
        """Test listing all patterns in a track."""
        repo = PatternRepository(session)

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
        session.tracks["0001"] = track

        patterns = repo.list_in_track("0001")
        assert len(patterns) == 2
        assert set(p.pattern_id for p in patterns) == {"0a1f", "0b2e"}

    def test_list_in_track_empty(self, session: Session) -> None:
        """Test listing patterns in track with no patterns."""
        repo = PatternRepository(session)

        track = Track(
            track_id="0001",
            track_name="kick",
            destination_id="sd",
            client_id="c1",
        )
        session.tracks["0001"] = track

        patterns = repo.list_in_track("0001")
        assert patterns == []

    def test_list_in_track_nonexistent(self, session: Session) -> None:
        """Test listing patterns in nonexistent track returns empty list."""
        repo = PatternRepository(session)
        patterns = repo.list_in_track("9999")
        assert patterns == []

    def test_list_all(self, session: Session) -> None:
        """Test listing all patterns across all tracks."""
        repo = PatternRepository(session)

        track1 = Track(
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
                )
            },
        )
        track2 = Track(
            track_id="0002",
            track_name="snare",
            destination_id="sd",
            client_id="c1",
            patterns={
                "0b2e": Pattern(
                    pattern_id="0b2e",
                    track_id="0002",
                    pattern_name="fill",
                    client_id="c1",
                ),
                "0c3d": Pattern(
                    pattern_id="0c3d",
                    track_id="0002",
                    pattern_name="main",
                    client_id="c1",
                ),
            },
        )
        session.tracks["0001"] = track1
        session.tracks["0002"] = track2

        all_patterns = repo.list_all()
        assert len(all_patterns) == 3

        # Verify tuples
        track_ids = [track_id for track_id, _ in all_patterns]
        pattern_ids = [pattern.pattern_id for _, pattern in all_patterns]
        assert set(pattern_ids) == {"0a1f", "0b2e", "0c3d"}

    def test_list_all_empty(self, session: Session) -> None:
        """Test listing all patterns when no tracks exist."""
        repo = PatternRepository(session)
        all_patterns = repo.list_all()
        assert all_patterns == []

    def test_remove_from_track(self, session: Session) -> None:
        """Test removing a pattern from a track."""
        repo = PatternRepository(session)

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
                )
            },
        )
        session.tracks["0001"] = track

        result = repo.remove_from_track("0001", "0a1f")
        assert result is True
        assert "0a1f" not in track.patterns

    def test_remove_from_track_nonexistent_pattern(self, session: Session) -> None:
        """Test removing nonexistent pattern returns False."""
        repo = PatternRepository(session)

        track = Track(
            track_id="0001",
            track_name="kick",
            destination_id="sd",
            client_id="c1",
        )
        session.tracks["0001"] = track

        result = repo.remove_from_track("0001", "9999")
        assert result is False

    def test_remove_from_track_nonexistent_track(self, session: Session) -> None:
        """Test removing from nonexistent track returns False."""
        repo = PatternRepository(session)
        result = repo.remove_from_track("9999", "0a1f")
        assert result is False
