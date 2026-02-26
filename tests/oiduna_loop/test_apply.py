"""
Tests for Apply functionality (v5)

Tests the pending change mechanism that allows changes
to be applied at musically appropriate moments.
"""

from __future__ import annotations

from typing import Any

from oiduna_core.ir.environment import Environment
from oiduna_core.ir.scene import Scene
from oiduna_core.ir.sequence import Event, EventSequence
from oiduna_core.ir.session import CompiledSession
from oiduna_core.ir.track import FxParams, Track, TrackMeta, TrackParams

from oiduna_loop.state import PendingApply, PlaybackState, RuntimeState


class TestPendingApply:
    """Test PendingApply dataclass."""

    def test_create_pending_apply(self):
        """PendingApply should store timing and data."""
        session = CompiledSession(
            environment=Environment(bpm=140.0),
        )
        pending = PendingApply(
            timing="bar",
            track_ids=["kick", "hihat"],
            session=session,
            scene_name=None,
        )

        assert pending.timing == "bar"
        assert pending.track_ids == ["kick", "hihat"]
        assert pending.session.environment.bpm == 140.0
        assert pending.received_at > 0


class TestRuntimeStateApply:
    """Test RuntimeState apply methods."""

    def test_set_pending_change(self):
        """set_pending_change should queue a change."""
        state = RuntimeState()
        data: dict[str, Any] = {
            "environment": {"bpm": 140.0},
            "tracks": {},
            "sequences": {},
        }

        state.set_pending_change(data, timing="bar", track_ids=["kick"])

        assert state.pending is not None
        assert state.pending.timing == "bar"
        assert state.pending.track_ids == ["kick"]

    def test_should_apply_pending_now(self):
        """timing='now' should always return True."""
        state = RuntimeState()
        state.set_pending_change({}, timing="now")

        assert state.should_apply_pending() is True

    def test_should_apply_pending_beat_at_boundary(self):
        """timing='beat' should apply at step 0, 4, 8, 12."""
        state = RuntimeState()
        state.set_pending_change({}, timing="beat")

        # At beat boundary
        state.position.step = 0
        assert state.should_apply_pending() is True

        state.position.step = 4
        assert state.should_apply_pending() is True

        state.position.step = 8
        assert state.should_apply_pending() is True

    def test_should_apply_pending_beat_not_at_boundary(self):
        """timing='beat' should not apply at non-boundary steps."""
        state = RuntimeState()
        state.set_pending_change({}, timing="beat")

        state.position.step = 1
        assert state.should_apply_pending() is False

        state.position.step = 7
        assert state.should_apply_pending() is False

    def test_should_apply_pending_bar_at_boundary(self):
        """timing='bar' should apply at step 0, 16, 32."""
        state = RuntimeState()
        state.set_pending_change({}, timing="bar")

        state.position.step = 0
        assert state.should_apply_pending() is True

        state.position.step = 16
        assert state.should_apply_pending() is True

        state.position.step = 32
        assert state.should_apply_pending() is True

    def test_should_apply_pending_bar_not_at_boundary(self):
        """timing='bar' should not apply at non-bar steps."""
        state = RuntimeState()
        state.set_pending_change({}, timing="bar")

        # Beat boundary but not bar
        state.position.step = 4
        assert state.should_apply_pending() is False

        state.position.step = 15
        assert state.should_apply_pending() is False

    def test_should_apply_pending_seq(self):
        """timing='seq' should only apply at step 0 after loop has progressed."""
        state = RuntimeState()
        state.set_pending_change({}, timing="seq")

        # At step 0 but loop hasn't progressed yet - should NOT apply
        state.position.step = 0
        assert state.should_apply_pending() is False

        # Simulate loop progression (step > 0)
        state.position.step = 16
        state.advance_step()  # This sets passed_non_zero = True
        assert state.should_apply_pending() is False  # Not at step 0

        # Now at step 0 with passed_non_zero = True - should apply
        state.position.step = 0
        assert state.should_apply_pending() is True

    def test_should_apply_pending_seq_immediate_at_zero(self):
        """timing='seq' at step 0 should wait for loop to progress first."""
        state = RuntimeState()
        state.position.step = 0  # Already at step 0

        state.set_pending_change({}, timing="seq")

        # Should NOT apply immediately even though we're at step 0
        assert state.should_apply_pending() is False

        # Advance through the loop
        for _ in range(16):  # Progress through some steps
            state.advance_step()

        # Still not at step 0
        assert state.should_apply_pending() is False

        # Continue until we wrap back to step 0
        while state.position.step != 0:
            state.advance_step()

        # Now should apply (at step 0 and passed_non_zero is True)
        assert state.should_apply_pending() is True

    def test_should_apply_pending_no_pending(self):
        """No pending change should return False."""
        state = RuntimeState()

        assert state.should_apply_pending() is False

    def test_apply_pending_changes_full_session(self):
        """apply_pending_changes should load full session when no track_ids."""
        state = RuntimeState()

        data: dict[str, Any] = {
            "environment": {"bpm": 140.0},
            "tracks": {
                "kick": {
                    "meta": {"track_id": "kick"},
                    "params": {"s": "bd"},
                    "fx": {},
                }
            },
            "sequences": {
                "kick": {
                    "track_id": "kick",
                    "events": [{"step": 0, "velocity": 1.0}],
                }
            },
        }

        state.set_pending_change(data, timing="now", track_ids=[])
        result = state.apply_pending_changes()

        assert result is True
        assert state.bpm == 140.0
        assert "kick" in state.tracks
        assert state.pending is None

    def test_apply_pending_changes_specific_tracks(self):
        """Specific tracks are updated and environment always applies."""
        state = RuntimeState()

        # Initial state with two tracks
        initial_data: dict[str, Any] = {
            "environment": {"bpm": 120.0},
            "tracks": {
                "kick": {
                    "meta": {"track_id": "kick"},
                    "params": {"s": "bd"},
                    "fx": {},
                },
                "hihat": {
                    "meta": {"track_id": "hihat"},
                    "params": {"s": "hh"},
                    "fx": {},
                },
            },
            "sequences": {
                "kick": {
                    "track_id": "kick",
                    "events": [{"step": 0, "velocity": 1.0}],
                },
                "hihat": {
                    "track_id": "hihat",
                    "events": [{"step": 2, "velocity": 0.5}],
                },
            },
        }
        state.load_compiled_session(initial_data)

        # Change only kick
        new_data: dict[str, Any] = {
            "environment": {"bpm": 140.0},
            "tracks": {
                "kick": {
                    "meta": {"track_id": "kick"},
                    "params": {"s": "super808"},
                    "fx": {},
                },
            },
            "sequences": {
                "kick": {
                    "track_id": "kick",
                    "events": [{"step": 4, "velocity": 0.8}],
                },
            },
        }

        state.set_pending_change(new_data, timing="now", track_ids=["kick"])
        state.apply_pending_changes()

        # kick should be updated
        assert state.tracks["kick"].params.s == "super808"
        kick_seq = state.sequences.get("kick")
        assert kick_seq is not None
        kick_events = list(kick_seq)
        assert len(kick_events) == 1
        assert kick_events[0].step == 4

        # hihat should have events CLEARED (exclusive apply)
        assert state.tracks["hihat"].params.s == "hh"  # Definition preserved
        hihat_seq = state.sequences.get("hihat")
        assert hihat_seq is not None
        assert len(list(hihat_seq)) == 0  # Events cleared

        # BPM should be updated (environment always applies)
        assert state.bpm == 140.0

    def test_apply_pending_clears_pending(self):
        """apply_pending_changes should clear pending."""
        state = RuntimeState()
        state.set_pending_change({}, timing="now")

        state.apply_pending_changes()

        assert state.pending is None

    def test_apply_pending_no_change_returns_false(self):
        """apply_pending_changes with no pending should return False."""
        state = RuntimeState()

        result = state.apply_pending_changes()

        assert result is False


class TestLoopEngineApply:
    """Test LoopEngine apply integration."""

    def test_compile_when_stopped_applies_immediately(
        self,
        test_engine,
        sample_session_data: dict[str, Any],
    ):
        """Compile when stopped should apply immediately."""
        test_engine._handle_compile(sample_session_data)

        assert "kick" in test_engine.state.tracks
        assert test_engine.state.pending is None

    def test_compile_when_playing_queues_change(
        self,
        test_engine,
        sample_session_data: dict[str, Any],
    ):
        """Compile when playing should queue change."""
        # Start playing
        test_engine._handle_play({})

        # Compile with apply info
        sample_session_data["apply"] = {"timing": "bar", "track_ids": []}
        test_engine._handle_compile(sample_session_data)

        # Should have pending change
        assert test_engine.state.pending is not None
        assert test_engine.state.pending.timing == "bar"

    def test_compile_with_now_applies_immediately_even_when_playing(
        self,
        test_engine,
        sample_session_data: dict[str, Any],
    ):
        """Compile with timing='now' should apply immediately."""
        # Start playing
        test_engine._handle_play({})

        # Compile with timing=now
        sample_session_data["apply"] = {"timing": "now", "track_ids": []}
        test_engine._handle_compile(sample_session_data)

        # Should have applied immediately
        assert "kick" in test_engine.state.tracks
        assert test_engine.state.pending is None

    def test_compile_without_apply_defaults_to_bar(
        self,
        test_engine,
        sample_session_data: dict[str, Any],
    ):
        """Compile without apply data should default to bar timing."""
        # Start playing
        test_engine._handle_play({})

        # Compile without apply
        test_engine._handle_compile(sample_session_data)

        # Should queue with bar timing
        assert test_engine.state.pending is not None
        assert test_engine.state.pending.timing == "bar"

    def test_compile_when_stopped_respects_track_ids(self, test_engine):
        """Compile when stopped should respect apply track_ids (exclusive apply)."""
        # Create session data with two tracks
        session_data: dict[str, Any] = {
            "environment": {"bpm": 140},
            "tracks": {
                "kick": {
                    "meta": {"track_id": "kick"},
                    "params": {"s": "super808"},
                    "fx": {},
                },
                "hihat": {
                    "meta": {"track_id": "hihat"},
                    "params": {"s": "hh"},
                    "fx": {},
                },
            },
            "sequences": {
                "kick": {
                    "track_id": "kick",
                    "events": [{"step": 0, "velocity": 1.0}],
                },
                "hihat": {
                    "track_id": "hihat",
                    "events": [{"step": 2, "velocity": 0.8}],
                },
            },
            "apply": {"timing": "bar", "track_ids": ["kick"]},  # Only apply kick
        }

        # Compile when stopped
        test_engine._handle_compile(session_data)

        # Both tracks should exist
        assert "kick" in test_engine.state.tracks
        assert "hihat" in test_engine.state.tracks

        # kick should have events
        kick_seq = test_engine.state.sequences.get("kick")
        assert kick_seq is not None
        kick_events = list(kick_seq)
        assert len(kick_events) == 1
        assert kick_events[0].step == 0

        # hihat should have events CLEARED (exclusive apply)
        hihat_seq = test_engine.state.sequences.get("hihat")
        assert hihat_seq is not None
        assert len(list(hihat_seq)) == 0

        # BPM should be updated
        assert test_engine.state.bpm == 140

    def test_compile_when_stopped_updates_bpm(self, test_engine):
        """Compile when stopped should update BPM from environment."""
        session_data: dict[str, Any] = {
            "environment": {"bpm": 180},
            "tracks": {},
            "sequences": {},
        }

        # Initial BPM
        assert test_engine.state.bpm == 120.0

        # Compile when stopped
        test_engine._handle_compile(session_data)

        # BPM should be updated
        assert test_engine.state.bpm == 180.0


class TestApplyTimingScenarios:
    """Integration scenarios for apply timing."""

    def test_bar_apply_waits_for_bar_boundary(self):
        """Changes with @bar should wait until bar boundary."""
        state = RuntimeState()
        state.playback_state = PlaybackState.PLAYING
        state.position.step = 5  # Mid-bar

        # Queue change
        data: dict[str, Any] = {
            "environment": {"bpm": 180},
            "tracks": {},
            "sequences": {},
        }
        state.set_pending_change(data, timing="bar")

        # Should not apply at step 5
        assert state.should_apply_pending() is False
        assert state.bpm == 120.0  # Unchanged

        # Advance to step 16 (bar boundary)
        state.position.step = 16
        assert state.should_apply_pending() is True

        state.apply_pending_changes()
        assert state.bpm == 180.0

    def test_beat_apply_waits_for_beat_boundary(self):
        """Changes with @beat should wait until beat boundary."""
        state = RuntimeState()
        state.playback_state = PlaybackState.PLAYING
        state.position.step = 1  # Mid-beat

        data: dict[str, Any] = {
            "environment": {"bpm": 180},
            "tracks": {},
            "sequences": {},
        }
        state.set_pending_change(data, timing="beat")

        # Should not apply at step 1
        assert state.should_apply_pending() is False

        # Advance to step 4 (beat boundary)
        state.position.step = 4
        assert state.should_apply_pending() is True

    def test_seq_apply_waits_for_loop_end(self):
        """Changes with @seq should wait until loop wraps back to step 0."""
        state = RuntimeState()
        state.playback_state = PlaybackState.PLAYING
        state.position.step = 15  # Near end of bar

        data: dict[str, Any] = {
            "environment": {"bpm": 180},
            "tracks": {},
            "sequences": {},
        }
        state.set_pending_change(data, timing="seq")

        # Should not apply at step 15
        assert state.should_apply_pending() is False

        # Manually set passed_non_zero (simulating loop progression)
        assert state.pending is not None
        state.pending.passed_non_zero = True

        # Now at step 0 (loop boundary) with passed_non_zero = True
        state.position.step = 0
        assert state.should_apply_pending() is True

    def test_seq_apply_requires_loop_progression(self):
        """@seq should not apply immediately even at step 0."""
        state = RuntimeState()
        state.playback_state = PlaybackState.PLAYING
        state.position.step = 0  # At loop start

        data: dict[str, Any] = {
            "environment": {"bpm": 180},
            "tracks": {},
            "sequences": {},
        }
        state.set_pending_change(data, timing="seq")

        # Should NOT apply immediately at step 0
        assert state.should_apply_pending() is False
        assert state.bpm == 120.0  # Unchanged

        # Advance through steps (16 steps)
        for _ in range(16):
            state.advance_step()

        # Still not at step 0 (we're at step 16)
        assert state.should_apply_pending() is False

        # Continue until we wrap back to step 0 (256 total steps)
        while state.position.step != 0:
            state.advance_step()

        # Now back at step 0 with passed_non_zero = True
        assert state.position.step == 0
        assert state.should_apply_pending() is True

        state.apply_pending_changes()
        assert state.bpm == 180.0


class TestExclusiveApply:
    """Test exclusive apply behavior (clear-then-apply)."""

    def test_apply_specific_tracks_clears_other_events(self):
        """@bar apply kick should clear hihat events."""
        state = RuntimeState()

        # Initial state with two tracks
        initial_data: dict[str, Any] = {
            "environment": {"bpm": 120.0},
            "tracks": {
                "kick": {
                    "meta": {"track_id": "kick"},
                    "params": {"s": "bd"},
                    "fx": {},
                },
                "hihat": {
                    "meta": {"track_id": "hihat"},
                    "params": {"s": "hh"},
                    "fx": {"room": 0.3},
                },
            },
            "sequences": {
                "kick": {
                    "track_id": "kick",
                    "events": [{"step": 0}],
                },
                "hihat": {
                    "track_id": "hihat",
                    "events": [{"step": 2}, {"step": 6}],
                },
            },
        }
        state.load_compiled_session(initial_data)

        # Apply only kick
        new_data: dict[str, Any] = {
            "environment": {"bpm": 120.0},
            "tracks": {
                "kick": {
                    "meta": {"track_id": "kick"},
                    "params": {"s": "bd"},
                    "fx": {},
                },
            },
            "sequences": {
                "kick": {
                    "track_id": "kick",
                    "events": [{"step": 0}, {"step": 8}],
                },
            },
        }
        state.set_pending_change(new_data, timing="now", track_ids=["kick"])
        state.apply_pending_changes()

        # kick should be updated
        kick_seq = state.sequences.get("kick")
        assert kick_seq is not None
        assert len(list(kick_seq)) == 2

        # hihat events should be cleared
        hihat_seq = state.sequences.get("hihat")
        assert hihat_seq is not None
        assert len(list(hihat_seq)) == 0

        # But hihat definition should be preserved
        assert state.tracks["hihat"].params.s == "hh"
        assert state.tracks["hihat"].fx.room == 0.3

    def test_apply_preserves_track_definitions(self):
        """Exclusive apply should preserve sound/fx settings."""
        state = RuntimeState()

        initial_data: dict[str, Any] = {
            "environment": {"bpm": 120.0},
            "tracks": {
                "kick": {
                    "meta": {"track_id": "kick"},
                    "params": {"s": "bd"},
                    "fx": {},
                },
                "snare": {
                    "meta": {"track_id": "snare"},
                    "params": {"s": "sn", "gain": 0.8},
                    "fx": {"delay_send": 0.2},
                },
            },
            "sequences": {
                "kick": {
                    "track_id": "kick",
                    "events": [{"step": 0}],
                },
                "snare": {
                    "track_id": "snare",
                    "events": [{"step": 4}],
                },
            },
        }
        state.load_compiled_session(initial_data)

        # Apply only kick
        new_data: dict[str, Any] = {
            "environment": {"bpm": 120.0},
            "tracks": {
                "kick": {
                    "meta": {"track_id": "kick"},
                    "params": {"s": "bd"},
                    "fx": {},
                }
            },
            "sequences": {
                "kick": {
                    "track_id": "kick",
                    "events": [{"step": 0}],
                }
            },
        }
        state.set_pending_change(new_data, timing="now", track_ids=["kick"])
        state.apply_pending_changes()

        # snare definition preserved
        assert state.tracks["snare"].params.s == "sn"
        assert state.tracks["snare"].params.gain == 0.8
        assert state.tracks["snare"].fx.delay_send == 0.2

        # snare events cleared
        snare_seq = state.sequences.get("snare")
        assert snare_seq is not None
        assert len(list(snare_seq)) == 0

    def test_apply_multiple_tracks_clears_others(self):
        """@bar apply kick, snare should clear only other tracks."""
        state = RuntimeState()

        initial_data: dict[str, Any] = {
            "environment": {"bpm": 120.0},
            "tracks": {
                "kick": {
                    "meta": {"track_id": "kick"},
                    "params": {"s": "bd"},
                    "fx": {},
                },
                "snare": {
                    "meta": {"track_id": "snare"},
                    "params": {"s": "sn"},
                    "fx": {},
                },
                "hihat": {
                    "meta": {"track_id": "hihat"},
                    "params": {"s": "hh"},
                    "fx": {},
                },
            },
            "sequences": {
                "kick": {
                    "track_id": "kick",
                    "events": [{"step": 0}],
                },
                "snare": {
                    "track_id": "snare",
                    "events": [{"step": 4}],
                },
                "hihat": {
                    "track_id": "hihat",
                    "events": [{"step": 2}],
                },
            },
        }
        state.load_compiled_session(initial_data)

        # Apply kick and snare
        new_data: dict[str, Any] = {
            "environment": {"bpm": 120.0},
            "tracks": {
                "kick": {
                    "meta": {"track_id": "kick"},
                    "params": {"s": "bd"},
                    "fx": {},
                },
                "snare": {
                    "meta": {"track_id": "snare"},
                    "params": {"s": "sn"},
                    "fx": {},
                },
            },
            "sequences": {
                "kick": {
                    "track_id": "kick",
                    "events": [{"step": 0}],
                },
                "snare": {
                    "track_id": "snare",
                    "events": [{"step": 4}],
                },
            },
        }
        state.set_pending_change(new_data, timing="now", track_ids=["kick", "snare"])
        state.apply_pending_changes()

        # kick and snare should have events
        kick_seq = state.sequences.get("kick")
        snare_seq = state.sequences.get("snare")
        assert kick_seq is not None
        assert snare_seq is not None
        assert len(list(kick_seq)) == 1
        assert len(list(snare_seq)) == 1

        # hihat should be cleared
        hihat_seq = state.sequences.get("hihat")
        assert hihat_seq is not None
        assert len(list(hihat_seq)) == 0


class TestSceneApply:
    """Test scene apply functionality."""

    def test_apply_scene_activates_scene(self):
        """Activating a scene should switch to that scene's state."""
        state = RuntimeState()

        # Create scene with lead track
        lead_track = Track(
            meta=TrackMeta(track_id="lead"),
            params=TrackParams(s="supersaw"),
            fx=FxParams(),
        )
        lead_events = [Event(step=0), Event(step=4)]

        drop_scene = Scene(
            name="drop",
            environment=Environment(bpm=130.0),
            tracks={"lead": lead_track},
            tracks_midi={},
            sequences={"lead": EventSequence.from_events("lead", lead_events)},
        )

        # Initial state with kick track
        kick_track = Track(
            meta=TrackMeta(track_id="kick"),
            params=TrackParams(s="bd"),
            fx=FxParams(),
        )
        kick_events = [Event(step=0)]

        initial_session = CompiledSession(
            environment=Environment(bpm=120.0),
            tracks={"kick": kick_track},
            sequences={"kick": EventSequence.from_events("kick", kick_events)},
            scenes={"drop": drop_scene},
        )
        state.load_session(initial_session)

        # Verify initial state
        assert state.bpm == 120.0
        assert "kick" in state.tracks

        # Apply scene "drop"
        result = state.apply_scene("drop")

        assert result is True
        assert state.current_scene == "drop"
        assert state.bpm == 130.0
        assert "lead" in state.tracks

        # Lead should have 2 events
        lead_seq = state.sequences.get("lead")
        assert lead_seq is not None
        assert len(list(lead_seq)) == 2

    def test_apply_nonexistent_scene_returns_false(self):
        """Applying non-existent scene should return False."""
        state = RuntimeState()

        result = state.apply_scene("nonexistent")

        assert result is False

    def test_scene_activation_clears_live_overrides(self):
        """Scene activation should clear live overrides."""
        state = RuntimeState()

        # Create scene
        lead_track = Track(
            meta=TrackMeta(track_id="lead"),
            params=TrackParams(s="supersaw"),
            fx=FxParams(),
        )
        scene = Scene(
            name="verse",
            environment=Environment(bpm=100.0),
            tracks={"lead": lead_track},
            tracks_midi={},
            sequences={},
        )

        # Initial session with scene
        initial_session = CompiledSession(
            environment=Environment(bpm=120.0),
            tracks={},
            sequences={},
            scenes={"verse": scene},
        )
        state.load_session(initial_session)

        # Apply some live overrides
        state.set_bpm(140.0)
        assert state.bpm == 140.0

        # Activate scene
        state.apply_scene("verse")

        # Scene BPM should take effect
        assert state.bpm == 100.0
        # Live overrides should be cleared
        assert state.live_overrides is None
