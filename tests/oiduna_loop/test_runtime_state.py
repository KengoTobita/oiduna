"""Tests for RuntimeState."""


from oiduna_core.ir.environment import Environment
from oiduna_core.ir.session import CompiledSession
from oiduna_core.ir.track import Track, TrackMeta, TrackParams
from oiduna_loop.state.runtime_state import (
    PlaybackState,
    Position,
    RuntimeState,
)


class TestPosition:
    """Test Position dataclass."""

    def test_default_values(self) -> None:
        """Test default position values."""
        pos = Position()
        assert pos.step == 0
        assert pos.bar == 0
        assert pos.beat == 0

    def test_advance(self) -> None:
        """Test advancing position."""
        pos = Position()
        pos.advance(256)
        assert pos.step == 1
        assert pos.beat == 0
        assert pos.bar == 0

    def test_advance_beat_boundary(self) -> None:
        """Test advancing to beat boundary."""
        pos = Position(step=3)
        pos.advance(256)
        assert pos.step == 4
        assert pos.beat == 1
        assert pos.bar == 0

    def test_advance_bar_boundary(self) -> None:
        """Test advancing to bar boundary."""
        pos = Position(step=15)
        pos.advance(256)
        assert pos.step == 16
        assert pos.beat == 0
        assert pos.bar == 1

    def test_advance_wrap_around(self) -> None:
        """Test wrapping around at loop end."""
        pos = Position(step=255)
        pos.advance(256)
        assert pos.step == 0
        assert pos.beat == 0
        assert pos.bar == 0

    def test_reset(self) -> None:
        """Test resetting position."""
        pos = Position(step=100, bar=6, beat=2)
        pos.reset()
        assert pos.step == 0
        assert pos.bar == 0
        assert pos.beat == 0

    def test_to_dict(self) -> None:
        """Test converting to dict."""
        pos = Position(step=16, bar=1, beat=0, timestamp=1234.5)
        d = pos.to_dict()
        assert d["step"] == 16
        assert d["bar"] == 1
        assert d["beat"] == 0
        assert d["timestamp"] == 1234.5


class TestRuntimeStateBasics:
    """Test RuntimeState basic functionality."""

    def test_default_state(self) -> None:
        """Test default state values."""
        state = RuntimeState()
        assert state.playback_state == PlaybackState.STOPPED
        assert state.playing is False
        assert state.bpm == 120.0
        assert state.loop_steps == 256

    def test_playing_property(self) -> None:
        """Test playing property getter/setter."""
        state = RuntimeState()
        assert state.playing is False

        state.playing = True
        assert state.playing is True
        assert state.playback_state == PlaybackState.PLAYING

        state.playing = False
        assert state.playing is False
        assert state.playback_state == PlaybackState.PAUSED

    def test_get_effective_empty(self) -> None:
        """Test get_effective with no state."""
        state = RuntimeState()
        eff = state.get_effective()
        assert isinstance(eff, CompiledSession)
        assert eff.environment.bpm == 120.0

    def test_get_effective_caching(self) -> None:
        """Test that get_effective caches results."""
        state = RuntimeState()
        eff1 = state.get_effective()
        eff2 = state.get_effective()
        assert eff1 is eff2  # Same object (cached)


class TestRuntimeStateSession:
    """Test RuntimeState session loading."""

    def test_load_session(self) -> None:
        """Test loading a session."""
        state = RuntimeState()
        session = CompiledSession(
            environment=Environment(bpm=140.0),
            tracks={
                "kick": Track(
                    meta=TrackMeta(track_id="kick"),
                    params=TrackParams(s="bd"),
                )
            },
        )

        state.load_session(session)
        eff = state.get_effective()

        assert eff.environment.bpm == 140.0
        assert "kick" in eff.tracks
        assert eff.tracks["kick"].params.s == "bd"

    def test_set_bpm(self) -> None:
        """Test changing BPM."""
        state = RuntimeState()
        state.load_session(CompiledSession(environment=Environment(bpm=120.0)))

        state.set_bpm(180.0)

        assert state.bpm == 180.0
        assert state.step_duration < 0.125  # Faster than 120 BPM


class TestRuntimeStateDeepMerge:
    """Test deep merge functionality."""

    def test_merge_environment(self) -> None:
        """Test merging environments."""
        state = RuntimeState()

        # Load base session
        state.load_session(CompiledSession(
            environment=Environment(bpm=120.0, scale="C_major"),
        ))

        # Apply override with different BPM
        state.apply_override(CompiledSession(
            environment=Environment(bpm=140.0),
        ))

        eff = state.get_effective()
        assert eff.environment.bpm == 140.0
        assert eff.environment.scale == "C_major"  # Kept from base

    def test_merge_tracks(self) -> None:
        """Test merging tracks."""
        state = RuntimeState()

        # Load base session with track
        state.load_session(CompiledSession(
            tracks={
                "kick": Track(
                    meta=TrackMeta(track_id="kick"),
                    params=TrackParams(s="bd", gain=0.8),
                )
            },
        ))

        # Apply override with different gain
        state.apply_override(CompiledSession(
            tracks={
                "kick": Track(
                    meta=TrackMeta(track_id="kick"),
                    params=TrackParams(s="bd", gain=0.5),
                )
            },
        ))

        eff = state.get_effective()
        assert eff.tracks["kick"].params.gain == 0.5

    def test_merge_adds_new_track(self) -> None:
        """Test that merge adds new tracks."""
        state = RuntimeState()

        state.load_session(CompiledSession(
            tracks={
                "kick": Track(
                    meta=TrackMeta(track_id="kick"),
                    params=TrackParams(s="bd"),
                )
            },
        ))

        state.apply_override(CompiledSession(
            tracks={
                "snare": Track(
                    meta=TrackMeta(track_id="snare"),
                    params=TrackParams(s="sd"),
                )
            },
        ))

        eff = state.get_effective()
        assert "kick" in eff.tracks
        assert "snare" in eff.tracks


class TestRuntimeStateScene:
    """Test scene activation."""

    def test_apply_scene(self) -> None:
        """Test activating a scene."""
        from oiduna_core.ir.scene import Scene

        state = RuntimeState()

        # Load session with scenes
        state.load_session(CompiledSession(
            scenes={
                "intro": Scene(
                    name="intro",
                    environment=Environment(bpm=100.0),
                    tracks={
                        "pad": Track(
                            meta=TrackMeta(track_id="pad"),
                            params=TrackParams(s="pad"),
                        )
                    },
                )
            },
        ))

        result = state.apply_scene("intro")
        assert result is True
        assert state.active_scene_name == "intro"

        eff = state.get_effective()
        assert eff.environment.bpm == 100.0
        assert "pad" in eff.tracks

    def test_apply_scene_not_found(self) -> None:
        """Test activating non-existent scene."""
        state = RuntimeState()
        result = state.apply_scene("nonexistent")
        assert result is False

    def test_apply_scene_clears_overrides(self) -> None:
        """Test that scene activation clears live_overrides."""
        from oiduna_core.ir.scene import Scene

        state = RuntimeState()

        state.load_session(CompiledSession(
            scenes={
                "drop": Scene(name="drop", environment=Environment(bpm=140.0))
            },
        ))

        # Add an override
        state.apply_override(CompiledSession(
            environment=Environment(bpm=120.0)
        ))

        # Activate scene should clear override
        state.apply_scene("drop")

        assert state.live_overrides is None
        assert state.bpm == 140.0


class TestRuntimeStatePending:
    """Test pending apply functionality."""

    def test_set_pending(self) -> None:
        """Test setting pending apply."""
        state = RuntimeState()
        session = CompiledSession()

        state.set_pending(session, timing="bar")

        assert state.pending is not None
        assert state.pending.timing == "bar"
        assert state.pending.session is session

    def test_should_apply_pending_now(self) -> None:
        """Test 'now' timing."""
        state = RuntimeState()
        state.set_pending(CompiledSession(), timing="now")
        assert state.should_apply_pending() is True

    def test_should_apply_pending_beat(self) -> None:
        """Test 'beat' timing."""
        state = RuntimeState()
        state.set_pending(CompiledSession(), timing="beat")

        # Step 0 is beat boundary
        state.position.step = 0
        assert state.should_apply_pending() is True

        # Step 1 is not
        state.position.step = 1
        assert state.should_apply_pending() is False

        # Step 4 is
        state.position.step = 4
        assert state.should_apply_pending() is True

    def test_should_apply_pending_bar(self) -> None:
        """Test 'bar' timing."""
        state = RuntimeState()
        state.set_pending(CompiledSession(), timing="bar")

        state.position.step = 0
        assert state.should_apply_pending() is True

        state.position.step = 4
        assert state.should_apply_pending() is False

        state.position.step = 16
        assert state.should_apply_pending() is True

    def test_should_apply_pending_seq(self) -> None:
        """Test 'seq' timing (wait for loop)."""
        state = RuntimeState()
        state.set_pending(CompiledSession(), timing="seq")

        # Step 0 but haven't passed non-zero yet
        state.position.step = 0
        assert state.should_apply_pending() is False

        # Advance to non-zero
        state.position.step = 1
        state.pending.passed_non_zero = True

        # Still not step 0
        assert state.should_apply_pending() is False

        # Back to step 0 after passing non-zero
        state.position.step = 0
        assert state.should_apply_pending() is True

    def test_execute_pending(self) -> None:
        """Test executing pending apply."""
        state = RuntimeState()
        session = CompiledSession(environment=Environment(bpm=160.0))

        state.set_pending(session, timing="now")
        result = state.execute_pending()

        assert result is True
        assert state.pending is None
        assert state.bpm == 160.0

    def test_execute_pending_none(self) -> None:
        """Test executing when no pending."""
        state = RuntimeState()
        result = state.execute_pending()
        assert result is False


class TestRuntimeStateActiveTracks:
    """Test active track filtering."""

    def test_get_active_tracks_no_mute_solo(self) -> None:
        """Test getting active tracks with no mute/solo."""
        state = RuntimeState()
        state.load_session(CompiledSession(
            tracks={
                "kick": Track(
                    meta=TrackMeta(track_id="kick"),
                    params=TrackParams(s="bd"),
                ),
                "snare": Track(
                    meta=TrackMeta(track_id="snare"),
                    params=TrackParams(s="sd"),
                ),
            },
        ))

        active = state.get_active_tracks()
        assert len(active) == 2
        assert "kick" in active
        assert "snare" in active

    def test_get_active_tracks_muted(self) -> None:
        """Test getting active tracks with mute."""
        state = RuntimeState()
        state.load_session(CompiledSession(
            tracks={
                "kick": Track(
                    meta=TrackMeta(track_id="kick", mute=True),
                    params=TrackParams(s="bd"),
                ),
                "snare": Track(
                    meta=TrackMeta(track_id="snare"),
                    params=TrackParams(s="sd"),
                ),
            },
        ))

        active = state.get_active_tracks()
        assert len(active) == 1
        assert "snare" in active

    def test_get_active_tracks_solo(self) -> None:
        """Test getting active tracks with solo."""
        state = RuntimeState()
        state.load_session(CompiledSession(
            tracks={
                "kick": Track(
                    meta=TrackMeta(track_id="kick", solo=True),
                    params=TrackParams(s="bd"),
                ),
                "snare": Track(
                    meta=TrackMeta(track_id="snare"),
                    params=TrackParams(s="sd"),
                ),
            },
        ))

        active = state.get_active_tracks()
        assert len(active) == 1
        assert "kick" in active


class TestRuntimeStateStatus:
    """Test status dict generation."""

    def test_to_status_dict(self) -> None:
        """Test converting to status dict."""
        state = RuntimeState()
        state.load_session(CompiledSession(
            environment=Environment(bpm=128.0),
            tracks={
                "kick": Track(
                    meta=TrackMeta(track_id="kick"),
                    params=TrackParams(s="bd"),
                ),
            },
        ))
        state.playback_state = PlaybackState.PLAYING
        state.position.step = 32

        status = state.to_status_dict()

        assert status["playing"] is True
        assert status["playback_state"] == "playing"
        assert status["bpm"] == 128.0
        assert status["position"]["step"] == 32
        assert "kick" in status["active_tracks"]
        assert status["has_pending"] is False
