"""Tests for SessionValidator.

Tests cover:
- Track ownership checking
- Pattern ownership checking
- Destination usage checking
- Client resource counting
- Boundary cases
"""

import pytest

from oiduna.domain.session.validator import SessionValidator
from oiduna.domain.models.session import Session
from oiduna.domain.models.track import Track
from oiduna.domain.models.pattern import Pattern


class TestCheckTrackOwnership:
    """Test check_track_ownership method."""

    def test_owner_returns_true(self, session):
        """Test that owner of track returns True."""
        # Add a track owned by client_1
        track = Track(track_id="0001", track_name="track1", client_id="client_1", destination_id="dest_1")
        session.tracks["0001"] = track

        result = SessionValidator.check_track_ownership(session, "0001", "client_1")

        assert result is True

    def test_non_owner_returns_false(self, session):
        """Test that non-owner of track returns False."""
        # Add a track owned by client_1
        track = Track(track_id="0001", track_name="track1", client_id="client_1", destination_id="dest_1")
        session.tracks["0001"] = track

        result = SessionValidator.check_track_ownership(session, "0001", "client_2")

        assert result is False

    def test_nonexistent_track_returns_false(self, session):
        """Test that nonexistent track returns False."""
        result = SessionValidator.check_track_ownership(session, "9999", "client_1")

        assert result is False

    def test_empty_session_returns_false(self, session):
        """Test that ownership check on empty session returns False."""
        result = SessionValidator.check_track_ownership(session, "0001", "client_1")

        assert result is False


class TestCheckPatternOwnership:
    """Test check_pattern_ownership method."""

    def test_owner_returns_true(self, session):
        """Test that owner of pattern returns True."""
        # Add track
        track = Track(track_id="0001", track_name="track1", client_id="client_1", destination_id="dest_1")
        # Track patterns are simple dicts in the actual implementation - check TrackRepository
        # Pattern ownership is checked via pattern["client_id"]
        track.patterns["0101"] = Pattern(
            pattern_id="0101", track_id="0001", pattern_name="pattern1",
            client_id="client_2", active=True, events=[]
        )
        session.tracks["0001"] = track

        result = SessionValidator.check_pattern_ownership(
            session, "0001", "0101", "client_2"
        )

        assert result is True

    def test_non_owner_returns_false(self, session):
        """Test that non-owner of pattern returns False."""
        # Add track
        track = Track(track_id="0001", track_name="track1", client_id="client_1", destination_id="dest_1")
        # Add pattern owned by client_2
        track.patterns["0101"] = Pattern(
            pattern_id="0101", track_id="0001", pattern_name="pattern1",
            client_id="client_2", active=True, events=[]
        )
        session.tracks["0001"] = track

        result = SessionValidator.check_pattern_ownership(
            session, "0001", "p001", "client_1"
        )

        assert result is False

    def test_nonexistent_track_returns_false(self, session):
        """Test that nonexistent track returns False."""
        result = SessionValidator.check_pattern_ownership(
            session, "9999", "0101", "client_1"
        )

        assert result is False

    def test_nonexistent_pattern_returns_false(self, session):
        """Test that nonexistent pattern returns False."""
        # Add track
        track = Track(track_id="0001", track_name="track1", client_id="client_1", destination_id="dest_1")
        session.tracks["0001"] = track

        result = SessionValidator.check_pattern_ownership(
            session, "0001", "9999", "client_1"
        )

        assert result is False

    def test_pattern_owned_by_different_client_than_track(self, session):
        """Test that pattern can be owned by different client than track."""
        track = Track(track_id="0001", track_name="track1", client_id="client_1", destination_id="dest_1")
        track.patterns["0101"] = Pattern(
            pattern_id="0101", track_id="0001", pattern_name="pattern1",
            client_id="client_2", active=True, events=[]
        )
        session.tracks["0001"] = track

        # Pattern is owned by client_2, not client_1
        assert SessionValidator.check_pattern_ownership(
            session, "0001", "0101", "client_2"
        ) is True
        assert SessionValidator.check_pattern_ownership(
            session, "0001", "0101", "client_1"
        ) is False


class TestCheckDestinationInUse:
    """Test check_destination_in_use method."""

    def test_destination_not_used_returns_empty_list(self, session):
        """Test that unused destination returns empty list."""
        result = SessionValidator.check_destination_in_use(session, "dest_1")

        assert result == []

    def test_destination_used_by_one_track(self, session):
        """Test that destination used by one track returns that track ID."""
        track = Track(track_id="0001", track_name="track1", client_id="client_1", destination_id="dest_1")
        session.tracks["0001"] = track

        result = SessionValidator.check_destination_in_use(session, "dest_1")

        assert result == ["0001"]

    def test_destination_used_by_multiple_tracks(self, session):
        """Test that destination used by multiple tracks returns all track IDs."""
        track1 = Track(track_id="0001", track_name="track1", client_id="client_1", destination_id="dest_1")
        track2 = Track(track_id="0002", track_name="track2", client_id="client_1", destination_id="dest_1")
        track3 = Track(track_id="0003", track_name="track3", client_id="client_2", destination_id="dest_2")
        session.tracks["0001"] = track1
        session.tracks["0002"] = track2
        session.tracks["0003"] = track3

        result = SessionValidator.check_destination_in_use(session, "dest_1")

        assert set(result) == {"0001", "0002"}

    def test_different_destinations_correctly_separated(self, session):
        """Test that tracks using different destinations are correctly separated."""
        track1 = Track(track_id="0001", track_name="track1", client_id="client_1", destination_id="dest_1")
        track2 = Track(track_id="0002", track_name="track2", client_id="client_1", destination_id="dest_2")
        session.tracks["0001"] = track1
        session.tracks["0002"] = track2

        result1 = SessionValidator.check_destination_in_use(session, "dest_1")
        result2 = SessionValidator.check_destination_in_use(session, "dest_2")

        assert result1 == ["0001"]
        assert result2 == ["0002"]

    def test_empty_session_returns_empty_list(self, session):
        """Test that checking destination in empty session returns empty list."""
        result = SessionValidator.check_destination_in_use(session, "any_dest")

        assert result == []


class TestGetClientResourceCount:
    """Test get_client_resource_count method."""

    def test_no_resources_returns_zero_counts(self, session):
        """Test that client with no resources returns zero counts."""
        result = SessionValidator.get_client_resource_count(session, "client_1")

        assert result == {"tracks": 0, "patterns": 0}

    def test_tracks_only_counted(self, session):
        """Test that client's tracks are counted."""
        track1 = Track(track_id="0001", track_name="track1", client_id="client_1", destination_id="dest_1")
        track2 = Track(track_id="0002", track_name="track2", client_id="client_1", destination_id="dest_1")
        track3 = Track(track_id="0003", track_name="track3", client_id="client_2", destination_id="dest_1")
        session.tracks["0001"] = track1
        session.tracks["0002"] = track2
        session.tracks["0003"] = track3

        result = SessionValidator.get_client_resource_count(session, "client_1")

        assert result["tracks"] == 2

    def test_patterns_counted(self, session):
        """Test that client's patterns are counted."""
        track1 = Track(track_id="0001", track_name="track1", client_id="client_1", destination_id="dest_1")
        track1.patterns["0101"] = Pattern(
            pattern_id="0101", track_id="0001", pattern_name="pattern1",
            client_id="client_1", active=True, events=[]
        )
        track1.patterns["0102"] = Pattern(
            pattern_id="0102", track_id="0001", pattern_name="pattern2",
            client_id="client_1", active=True, events=[]
        )
        session.tracks["0001"] = track1

        result = SessionValidator.get_client_resource_count(session, "client_1")

        assert result["patterns"] == 2

    def test_patterns_in_other_clients_tracks_counted(self, session):
        """Test that only patterns in client's own tracks are counted."""
        # Track owned by client_1
        track1 = Track(track_id="0001", track_name="track1", client_id="client_1", destination_id="dest_1")
        # Pattern owned by client_2, but in client_1's track
        track1.patterns["0101"] = Pattern(
            pattern_id="0101", track_id="0001", pattern_name="pattern1",
            client_id="client_2", active=True, events=[]
        )
        session.tracks["0001"] = track1

        result = SessionValidator.get_client_resource_count(session, "client_2")

        # client_2 owns 0 tracks and 0 patterns (pattern is in client_1's track, not counted)
        assert result["tracks"] == 0
        assert result["patterns"] == 0

    def test_mixed_ownership_counted_correctly(self, session):
        """Test that mixed ownership is counted correctly."""
        # Track 1: client_1 track with client_1 and client_2 patterns
        track1 = Track(track_id="0001", track_name="track1", client_id="client_1", destination_id="dest_1")
        track1.patterns["0101"] = Pattern(
            pattern_id="0101", track_id="0001", pattern_name="pattern1",
            client_id="client_1", active=True, events=[]
        )
        track1.patterns["0103"] = Pattern(
            pattern_id="0103", track_id="0001", pattern_name="pattern2",
            client_id="client_2", active=True, events=[]
        )

        # Track 2: client_2 track with client_1 pattern
        track2 = Track(track_id="0002", track_name="track2", client_id="client_2", destination_id="dest_1")
        track2.patterns["0201"] = Pattern(
            pattern_id="0201", track_id="0002", pattern_name="pattern3",
            client_id="client_1", active=True, events=[]
        )

        session.tracks["0001"] = track1
        session.tracks["0002"] = track2

        result1 = SessionValidator.get_client_resource_count(session, "client_1")
        result2 = SessionValidator.get_client_resource_count(session, "client_2")

        # client_1: 1 track (track1), 1 pattern in own track (0101)
        assert result1["tracks"] == 1
        assert result1["patterns"] == 1

        # client_2: 1 track (track2), 0 patterns in own track
        # (0103 is in track1 owned by client_1, so not counted)
        assert result2["tracks"] == 1
        assert result2["patterns"] == 0

    def test_empty_session_returns_zero_counts(self, session):
        """Test that empty session returns zero counts."""
        result = SessionValidator.get_client_resource_count(session, "client_1")

        assert result == {"tracks": 0, "patterns": 0}

    def test_many_resources_counted_correctly(self, session):
        """Test that large number of resources are counted correctly."""
        # Create 10 tracks for client_1, each with 5 patterns
        for i in range(10):
            track_id = f"{i:04x}"  # Convert to 4-digit hex
            track = Track(
                track_id=track_id,
                track_name=f"track{i}",
                client_id="client_1",
                destination_id="dest_1"
            )
            for j in range(5):
                # パターンIDを4桁の16進数形式で生成: トラック番号(2桁) + パターン番号(2桁)
                pattern_id = f"{i:02x}{j:02x}"
                track.patterns[pattern_id] = Pattern(
                    pattern_id=pattern_id,
                    track_id=track_id,
                    pattern_name=f"pattern{i}{j}",
                    client_id="client_1",
                    active=True,
                    events=[]
                )
            session.tracks[track_id] = track

        result = SessionValidator.get_client_resource_count(session, "client_1")

        assert result["tracks"] == 10
        assert result["patterns"] == 50


class TestBoundaryCases:
    """Test boundary conditions."""

    def test_empty_client_id(self, session):
        """Test with empty client ID."""
        result = SessionValidator.get_client_resource_count(session, "")

        assert result == {"tracks": 0, "patterns": 0}

    def test_empty_track_id(self, session):
        """Test ownership check with empty track ID."""
        result = SessionValidator.check_track_ownership(session, "", "client_1")

        assert result is False

    def test_empty_pattern_id(self, session):
        """Test pattern ownership check with empty pattern ID."""
        track = Track(track_id="0001", track_name="track1", client_id="client_1", destination_id="dest_1")
        session.tracks["0001"] = track

        result = SessionValidator.check_pattern_ownership(session, "0001", "", "client_1")

        assert result is False

    def test_track_with_no_patterns(self, session):
        """Test resource count for track with no patterns."""
        track = Track(track_id="0001", track_name="track1", client_id="client_1", destination_id="dest_1")
        session.tracks["0001"] = track

        result = SessionValidator.get_client_resource_count(session, "client_1")

        assert result["tracks"] == 1
        assert result["patterns"] == 0
