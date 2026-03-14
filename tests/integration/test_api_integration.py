"""Integration tests for API routes with new Repository/Service architecture."""

import pytest
from oiduna.domain.models import OscDestinationConfig
from oiduna.domain.session.container import SessionContainer


class TestAPIIntegration:
    """Test that API-like workflows work with new architecture."""

    def test_track_workflow(self) -> None:
        """Test complete track workflow (mimics API calls)."""
        container = SessionContainer()

        # Setup: Create destination and client (like admin would do)
        container.destination_repo.save(
            OscDestinationConfig(
                id="superdirt",
                type="osc",
                host="127.0.0.1",
                port=57120,
                address="/dirt/play",
            )
        )
        client = container.clients.create("alice_001", "Alice", "mars")

        # API: POST /tracks
        track = container.tracks.create(
            track_name="kick",
            destination_id="superdirt",
            client_id=client.client_id,
            base_params={"sound": "bd", "orbit": 0},
        )
        assert track.track_name == "kick"
        assert track.client_id == "alice_001"

        # API: GET /tracks
        tracks = container.tracks.list_tracks()
        assert len(tracks) == 1
        assert tracks[0].track_id == track.track_id

        # API: GET /tracks/{track_id}
        retrieved = container.tracks.get(track.track_id)
        assert retrieved is not None
        assert retrieved.track_name == "kick"

        # API: PATCH /tracks/{track_id}
        updated = container.tracks.update_base_params(
            track.track_id, {"gain": 0.8}
        )
        assert updated is not None
        assert updated.base_params["gain"] == 0.8
        assert updated.base_params["sound"] == "bd"  # Shallow merge

        # API: DELETE /tracks/{track_id}
        deleted = container.tracks.delete(track.track_id)
        assert deleted is True
        assert container.tracks.get(track.track_id) is None

    def test_pattern_workflow(self) -> None:
        """Test complete pattern workflow (mimics API calls)."""
        container = SessionContainer()

        # Setup
        container.destination_repo.save(
            OscDestinationConfig(
                id="sd", type="osc", host="127.0.0.1", port=57120, address="/dirt/play"
            )
        )
        client = container.clients.create("alice", "Alice")
        track = container.tracks.create("kick", "sd", "alice")

        # API: POST /patterns (flat)
        pattern = container.patterns.create(
            track_id=track.track_id,
            pattern_name="main",
            client_id="alice",
            active=True,
        )
        assert pattern.pattern_name == "main"
        assert pattern.active is True
        assert pattern.archived is False

        # API: GET /patterns (flat)
        all_patterns = container.patterns.list_all(include_archived=False)
        assert len(all_patterns) == 1

        # API: GET /patterns/{pattern_id} (flat)
        retrieved = container.patterns.get_by_id(pattern.pattern_id)
        assert retrieved is not None
        assert retrieved.pattern_id == pattern.pattern_id

        # API: GET /tracks/{track_id}/patterns (hierarchical)
        track_patterns = container.patterns.list_patterns(
            track.track_id, include_archived=False
        )
        assert track_patterns is not None
        assert len(track_patterns) == 1

        # API: PATCH /patterns/{pattern_id}
        updated = container.patterns.update(
            pattern.pattern_id, active=False
        )
        assert updated is not None
        assert updated.active is False

        # API: DELETE /patterns/{pattern_id} (soft delete)
        deleted = container.patterns.delete(pattern.pattern_id)
        assert deleted is True

        # Pattern still exists but archived
        archived = container.patterns.get_by_id(pattern.pattern_id)
        assert archived is not None
        assert archived.archived is True

        # Not in default list
        visible = container.patterns.list_all(include_archived=False)
        assert len(visible) == 0

        # In archived list
        with_archived = container.patterns.list_all(include_archived=True)
        assert len(with_archived) == 1

        # API: PATCH /patterns/{pattern_id} (restore)
        restored = container.patterns.update(
            pattern.pattern_id, archived=False
        )
        assert restored is not None
        assert restored.archived is False

    def test_pattern_move_workflow(self) -> None:
        """Test moving pattern between tracks (mimics API)."""
        container = SessionContainer()

        # Setup
        container.destination_repo.save(
            OscDestinationConfig(
                id="sd", type="osc", host="127.0.0.1", port=57120, address="/dirt/play"
            )
        )
        client = container.clients.create("alice", "Alice")
        track1 = container.tracks.create("kick", "sd", "alice")
        track2 = container.tracks.create("snare", "sd", "alice")
        pattern = container.patterns.create(track1.track_id, "main", "alice")

        # API: PATCH /patterns/{pattern_id} with track_id (move)
        moved = container.patterns.update(
            pattern.pattern_id, track_id=track2.track_id
        )
        assert moved is not None
        assert moved.track_id == track2.track_id

        # Verify pattern is in new track
        track1_patterns = container.patterns.list_patterns(
            track1.track_id, include_archived=False
        )
        track2_patterns = container.patterns.list_patterns(
            track2.track_id, include_archived=False
        )
        assert len(track1_patterns) == 0
        assert len(track2_patterns) == 1

    def test_timeline_workflow(self) -> None:
        """Test timeline workflow (mimics API calls)."""
        from oiduna.domain.schedule.models import LoopSchedule

        container = SessionContainer()

        # API: POST /timeline/cue
        batch = LoopSchedule(entries=())
        success, msg, change_id = container.timeline.cue_change(
            batch=batch,
            target_global_step=100,
            client_id="alice",
            client_name="Alice",
            description="Test change",
            current_global_step=50,
        )
        assert success is True
        assert change_id is not None

        # API: GET /timeline/changes/{change_id}
        change = container.timeline.get_change(change_id)
        assert change is not None
        assert change.client_id == "alice"

        # API: GET /timeline/upcoming
        upcoming = container.timeline.get_all_upcoming(
            current_global_step=75, limit=100
        )
        assert len(upcoming) == 1

        # API: PATCH /timeline/changes/{change_id}
        new_batch = LoopSchedule(entries=())
        updated_success, updated_msg = container.timeline.update_change(
            change_id=change_id,
            new_batch=new_batch,
            new_target_global_step=150,
            new_description="Updated",
            client_id="alice",
            current_global_step=60,
        )
        assert updated_success is True

        # API: DELETE /timeline/changes/{change_id}
        cancelled_success, cancelled_msg = container.timeline.cancel_change(
            change_id, client_id="alice"
        )
        assert cancelled_success is True
        assert container.timeline.get_change(change_id) is None

    def test_environment_workflow(self) -> None:
        """Test environment workflow (mimics API calls)."""
        container = SessionContainer()

        # API: PATCH /session/environment
        updated = container.environment.update(
            bpm=140.0, metadata={"key": "Am", "scale": "minor"}
        )
        assert updated["bpm"] == 140.0
        assert updated["metadata"] == {"key": "Am", "scale": "minor"}

        # API: GET /session (includes environment)
        session = container.get_state()
        assert session.environment.bpm == 140.0
        assert session.environment.metadata == {"key": "Am", "scale": "minor"}

    def test_client_auth_workflow(self) -> None:
        """Test client authentication workflow (mimics API calls)."""
        container = SessionContainer()

        # API: POST /auth/connect
        client = container.clients.create("alice_001", "Alice", "mars")
        assert client.token  # Token generated

        # API: GET /auth/verify (simulated)
        verified = container.clients.get("alice_001")
        assert verified is not None
        # In real API, would check: verified.token == provided_token

        # API: DELETE /auth/disconnect
        deleted = container.clients.delete("alice_001")
        assert deleted is True

    def test_cascade_delete_workflow(self) -> None:
        """Test cascade delete (track deletes patterns)."""
        container = SessionContainer()

        # Setup
        container.destination_repo.save(
            OscDestinationConfig(
                id="sd", type="osc", host="127.0.0.1", port=57120, address="/dirt/play"
            )
        )
        client = container.clients.create("alice", "Alice")
        track = container.tracks.create("kick", "sd", "alice")
        pattern1 = container.patterns.create(track.track_id, "main", "alice")
        pattern2 = container.patterns.create(track.track_id, "fill", "alice")

        # API: DELETE /tracks/{track_id}
        deleted = container.tracks.delete(track.track_id)
        assert deleted is True

        # Patterns should be gone too
        assert container.patterns.get_by_id(pattern1.pattern_id) is None
        assert container.patterns.get_by_id(pattern2.pattern_id) is None

    def test_validation_errors(self) -> None:
        """Test that validation errors are raised correctly."""
        container = SessionContainer()

        # Try to create track with non-existent destination
        with pytest.raises(ValueError, match="Destination.*does not exist"):
            container.tracks.create("kick", "nonexistent", "alice")

        # Try to create track with non-existent client
        container.destination_repo.save(
            OscDestinationConfig(
                id="sd", type="osc", host="127.0.0.1", port=57120, address="/dirt/play"
            )
        )
        with pytest.raises(ValueError, match="Client.*does not exist"):
            container.tracks.create("kick", "sd", "nonexistent")

        # Try to create pattern with non-existent track
        container.clients.create("alice", "Alice")
        with pytest.raises(ValueError, match="Track.*not found"):
            container.patterns.create("9999", "main", "alice")
