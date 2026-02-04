"""
Oiduna Loop Runtime State

Manages runtime state for the loop engine using v5 shared models.
Implements scene_state + live_overrides pattern with deep merging.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from oiduna_core.constants.steps import LOOP_STEPS
from oiduna_core.ir.environment import Environment
from oiduna_core.ir.sequence import EventSequence
from oiduna_core.ir.session import ApplyTiming, CompiledSession
from oiduna_core.ir.track import FxParams, Track, TrackMeta, TrackParams

if TYPE_CHECKING:
    from oiduna_core.ir.track_midi import TrackMidi

# Timing constants (16th note resolution)
STEPS_PER_BEAT = 4   # 4 steps (16th notes) per beat
STEPS_PER_BAR = 16   # 16 steps per bar (4/4 time)


class PlaybackState(Enum):
    """Playback state enumeration"""
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"


@dataclass
class Position:
    """Current playback position"""
    step: int = 0
    bar: int = 0
    beat: int = 0
    timestamp: float = 0.0

    def advance(self, loop_steps: int = LOOP_STEPS) -> None:
        """Advance by one step"""
        self.step = (self.step + 1) % loop_steps
        self.beat = (self.step // STEPS_PER_BEAT) % STEPS_PER_BEAT
        self.bar = self.step // STEPS_PER_BAR
        self.timestamp = time.time()

    def reset(self) -> None:
        """Reset position to start"""
        self.step = 0
        self.bar = 0
        self.beat = 0
        self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for IPC"""
        return {
            "step": self.step,
            "bar": self.bar,
            "beat": self.beat,
            "timestamp": self.timestamp,
        }


@dataclass
class PendingApply:
    """Pending apply waiting to be executed"""
    timing: ApplyTiming
    session: CompiledSession
    track_ids: list[str]
    scene_name: str | None
    received_at: float = field(default_factory=time.time)
    passed_non_zero: bool = False  # For "seq" timing


@dataclass
class RuntimeState:
    """
    Runtime state for the loop engine.

    Uses scene_state + live_overrides pattern:
    - scene_state: Base state from scene activation
    - live_overrides: Incremental changes during live coding
    - _effective: Cached merged state for performance
    """

    # Scene + Overrides
    active_scene_name: str | None = None
    scene_state: CompiledSession | None = None
    live_overrides: CompiledSession | None = None

    # Cached effective state
    _effective: CompiledSession | None = field(default=None, repr=False)

    # Playback
    position: Position = field(default_factory=Position)
    playback_state: PlaybackState = PlaybackState.STOPPED

    # Pending apply
    pending: PendingApply | None = None

    # Timing (derived from BPM)
    _step_duration: float = 0.125  # 120 BPM default
    _cps: float = 0.5  # cycles per second

    @property
    def playing(self) -> bool:
        """Check if actively playing"""
        return self.playback_state == PlaybackState.PLAYING

    @playing.setter
    def playing(self, value: bool) -> None:
        """Backwards compatible setter"""
        if value:
            self.playback_state = PlaybackState.PLAYING
        elif self.playback_state == PlaybackState.PLAYING:
            self.playback_state = PlaybackState.PAUSED

    @property
    def bpm(self) -> float:
        """Get current BPM"""
        eff = self.get_effective()
        return float(eff.environment.bpm)

    @property
    def step_duration(self) -> float:
        """Get step duration in seconds"""
        return self._step_duration

    @property
    def cps(self) -> float:
        """Get cycles per second for SuperDirt"""
        return self._cps

    @property
    def loop_steps(self) -> int:
        """Get loop length in steps (always 256 in v5)"""
        return int(LOOP_STEPS)

    def get_effective(self) -> CompiledSession:
        """
        Get effective session state.

        Merges scene_state and live_overrides with deep merge.
        Results are cached until state changes.
        """
        if self._effective is not None:
            return self._effective

        if self.scene_state is None and self.live_overrides is None:
            self._effective = CompiledSession()
        elif self.scene_state is None:
            self._effective = self.live_overrides
        elif self.live_overrides is None:
            self._effective = self.scene_state
        else:
            self._effective = self._deep_merge(self.scene_state, self.live_overrides)

        self._update_timing()
        assert self._effective is not None
        return self._effective

    def _deep_merge(
        self, base: CompiledSession, overrides: CompiledSession
    ) -> CompiledSession:
        """
        Deep merge two CompiledSessions.

        Override properties take precedence, base values used as fallback.
        """
        merged_env = self._merge_environment(base.environment, overrides.environment)

        # Tracks: merge by track_id
        merged_tracks = dict(base.tracks)
        for track_id, track in overrides.tracks.items():
            if track_id in merged_tracks:
                merged_tracks[track_id] = self._merge_track(
                    merged_tracks[track_id], track
                )
            else:
                merged_tracks[track_id] = track

        # MIDI tracks: simple update
        merged_tracks_midi = dict(base.tracks_midi)
        merged_tracks_midi.update(overrides.tracks_midi)

        # Mixer lines: merge
        merged_mixer_lines = dict(base.mixer_lines)
        merged_mixer_lines.update(overrides.mixer_lines)

        # Sequences: update
        merged_sequences = dict(base.sequences)
        merged_sequences.update(overrides.sequences)

        # Scenes: update
        merged_scenes = dict(base.scenes)
        merged_scenes.update(overrides.scenes)

        return CompiledSession(
            environment=merged_env,
            tracks=merged_tracks,
            tracks_midi=merged_tracks_midi,
            mixer_lines=merged_mixer_lines,
            sequences=merged_sequences,
            scenes=merged_scenes,
            apply=overrides.apply or base.apply,
        )

    def _merge_environment(
        self, base: Environment, override: Environment
    ) -> Environment:
        """Merge environment settings (override wins for non-default values)"""
        return Environment(
            bpm=override.bpm if override.bpm != 120.0 else base.bpm,
            scale=override.scale if override.scale != "C_major" else base.scale,
            default_gate=(
                override.default_gate if override.default_gate != 1.0 else base.default_gate
            ),
            swing=override.swing if override.swing != 0.0 else base.swing,
            loop_steps=LOOP_STEPS,  # Always 256 in v5
            chords=override.chords if override.chords else base.chords,
        )

    def _merge_track(self, base: Track, override: Track) -> Track:
        """Merge track settings (override wins for non-default values)"""
        merged_params = TrackParams(
            s=override.params.s or base.params.s,
            s_path=override.params.s_path or base.params.s_path,
            n=override.params.n if override.params.n != 0 else base.params.n,
            gain=override.params.gain if override.params.gain != 1.0 else base.params.gain,
            pan=override.params.pan if override.params.pan != 0.5 else base.params.pan,
            speed=override.params.speed if override.params.speed != 1.0 else base.params.speed,
            begin=override.params.begin if override.params.begin != 0.0 else base.params.begin,
            end=override.params.end if override.params.end != 1.0 else base.params.end,
            orbit=override.params.orbit if override.params.orbit != 0 else base.params.orbit,
            cut=override.params.cut if override.params.cut is not None else base.params.cut,
            legato=(
                override.params.legato
                if override.params.legato is not None
                else base.params.legato
            ),
        )

        # Merge FX
        merged_fx_dict = base.fx.to_dict()
        merged_fx_dict.update(override.fx.to_dict())
        merged_fx = FxParams.from_dict(merged_fx_dict)

        # Merge modulations
        merged_mods = dict(base.modulations)
        merged_mods.update(override.modulations)

        return Track(
            meta=override.meta,
            params=merged_params,
            fx=merged_fx,
            track_fx=override.track_fx,
            sends=override.sends or base.sends,
            modulations=merged_mods,
        )

    def _update_timing(self) -> None:
        """Update timing calculations from BPM"""
        bpm = self.bpm
        self._step_duration = 60.0 / bpm / 4
        self._cps = bpm / 60.0 / 4

    def set_bpm(self, bpm: float) -> None:
        """Update BPM dynamically"""
        bpm = max(1.0, min(999.0, bpm))
        eff = self.get_effective()
        # Create new environment with updated BPM
        new_env = Environment(
            bpm=bpm,
            scale=eff.environment.scale,
            default_gate=eff.environment.default_gate,
            swing=eff.environment.swing,
            loop_steps=LOOP_STEPS,
            chords=eff.environment.chords,
        )

        if self.live_overrides is None:
            self.live_overrides = CompiledSession(environment=new_env)
        else:
            self.live_overrides = CompiledSession(
                environment=new_env,
                tracks=self.live_overrides.tracks,
                tracks_midi=self.live_overrides.tracks_midi,
                mixer_lines=self.live_overrides.mixer_lines,
                sequences=self.live_overrides.sequences,
                scenes=self.live_overrides.scenes,
                apply=self.live_overrides.apply,
            )

        self._effective = None
        self._update_timing()

    def apply_scene(self, scene_name: str) -> bool:
        """
        Activate a scene by name.

        Clears live_overrides and sets scene_state from the scene.
        """
        eff = self.get_effective()
        if scene_name not in eff.scenes:
            return False

        scene = eff.scenes[scene_name]
        self.active_scene_name = scene_name
        self.scene_state = CompiledSession(
            environment=scene.environment or Environment(),
            tracks=scene.tracks,
            tracks_midi=scene.tracks_midi,
            sequences=scene.sequences,
            scenes=eff.scenes,  # Keep scenes available
        )
        self.live_overrides = None
        self._effective = None
        self._update_timing()
        return True

    def apply_override(self, override: CompiledSession) -> None:
        """Apply incremental override during live coding"""
        if self.live_overrides is None:
            self.live_overrides = override
        else:
            self.live_overrides = self._deep_merge(self.live_overrides, override)
        self._effective = None
        self._update_timing()

    def load_session(self, session: CompiledSession) -> None:
        """Load a full session (replaces everything)"""
        self.scene_state = session
        self.live_overrides = None
        self.active_scene_name = None
        self._effective = None
        self._update_timing()

    def advance_step(self) -> None:
        """Advance playback position by one step"""
        self.position.advance(LOOP_STEPS)

        # Update pending state for "seq" timing
        if (self.pending
                and self.pending.timing == "seq"
                and self.position.step > 0):
            self.pending.passed_non_zero = True

    def reset_position(self) -> None:
        """Reset playback position to start"""
        self.position.reset()

    def set_pending(
        self,
        session: CompiledSession,
        timing: ApplyTiming = "bar",
        track_ids: list[str] | None = None,
        scene_name: str | None = None,
    ) -> None:
        """Queue a pending apply"""
        self.pending = PendingApply(
            timing=timing,
            session=session,
            track_ids=track_ids or [],
            scene_name=scene_name,
        )

    def should_apply_pending(self) -> bool:
        """Check if pending apply should be executed at current step"""
        if self.pending is None:
            return False

        step = self.position.step
        timing = self.pending.timing

        if timing == "now":
            return True
        elif timing == "beat":
            return step % STEPS_PER_BEAT == 0
        elif timing == "bar":
            return step % STEPS_PER_BAR == 0
        elif timing == "seq":
            return step == 0 and self.pending.passed_non_zero

        return False

    def execute_pending(self) -> bool:
        """Execute pending apply if exists"""
        if self.pending is None:
            return False

        if self.pending.scene_name:
            # Scene apply
            self.apply_scene(self.pending.scene_name)
        elif not self.pending.track_ids:
            # Full session apply
            if self.active_scene_name:
                self.apply_override(self.pending.session)
            else:
                self.load_session(self.pending.session)
        else:
            # Partial apply (specific tracks)
            self._apply_partial(self.pending.session, self.pending.track_ids)

        self.pending = None
        return True

    def _apply_partial(
        self, session: CompiledSession, track_ids: list[str]
    ) -> None:
        """Apply only specific tracks from session"""
        partial_tracks = {
            tid: track
            for tid, track in session.tracks.items()
            if tid in track_ids
        }
        partial_tracks_midi = {
            tid: track
            for tid, track in session.tracks_midi.items()
            if tid in track_ids
        }
        partial_sequences = {
            tid: seq
            for tid, seq in session.sequences.items()
            if tid in track_ids
        }

        partial_session = CompiledSession(
            environment=session.environment,
            tracks=partial_tracks,
            tracks_midi=partial_tracks_midi,
            sequences=partial_sequences,
        )

        self.apply_override(partial_session)

        # Clear events for non-specified tracks (exclusive apply)
        self._clear_non_specified_events(track_ids)

    def _clear_non_specified_events(self, specified_ids: list[str]) -> None:
        """Clear events for tracks not in specified list"""
        preserved = set(specified_ids)
        eff = self.get_effective()

        # Create override with empty sequences for non-specified tracks
        empty_sequences = {}
        for track_id in eff.sequences:
            if track_id not in preserved:
                empty_sequences[track_id] = EventSequence(track_id=track_id)

        if empty_sequences:
            self.apply_override(CompiledSession(sequences=empty_sequences))

    def get_active_tracks(self) -> dict[str, Track]:
        """Get tracks that should produce sound (respecting mute/solo)"""
        eff = self.get_effective()
        has_solo = any(t.meta.solo for t in eff.tracks.values())

        if has_solo:
            return {k: v for k, v in eff.tracks.items() if v.meta.solo}
        else:
            return {k: v for k, v in eff.tracks.items() if not v.meta.mute}

    def get_active_tracks_midi(self) -> dict[str, TrackMidi]:
        """Get MIDI tracks that should produce sound"""
        eff = self.get_effective()
        has_solo = any(t.solo for t in eff.tracks_midi.values())

        if has_solo:
            return {k: v for k, v in eff.tracks_midi.items() if v.solo}
        else:
            return {k: v for k, v in eff.tracks_midi.items() if not v.mute}

    def to_status_dict(self) -> dict[str, Any]:
        """Convert to status message format"""
        eff = self.get_effective()
        return {
            "playing": self.playing,
            "playback_state": self.playback_state.value,
            "bpm": self.bpm,
            "position": self.position.to_dict(),
            "active_tracks": list(self.get_active_tracks().keys()),
            "has_pending": self.pending is not None,
            "scenes": list(eff.scenes.keys()),
            "current_scene": self.active_scene_name,
        }

    # ============================================================
    # Compatibility Methods (for SessionState migration)
    # ============================================================

    @property
    def tracks(self) -> dict[str, Track]:
        """Get all tracks (for backward compatibility)"""
        eff = self.get_effective()
        return dict(eff.tracks)

    @property
    def tracks_midi(self) -> dict[str, TrackMidi]:
        """Get all MIDI tracks (for backward compatibility)"""
        eff = self.get_effective()
        return dict(eff.tracks_midi)

    @property
    def sequences(self) -> dict[str, EventSequence]:
        """Get all sequences (for backward compatibility)"""
        eff = self.get_effective()
        return dict(eff.sequences)

    @property
    def scenes(self) -> dict[str, Any]:
        """Get all scenes (for backward compatibility)"""
        eff = self.get_effective()
        return dict(eff.scenes)

    @property
    def current_scene(self) -> str | None:
        """Get current scene name (for backward compatibility)"""
        return self.active_scene_name

    def load_compiled_session(self, data: dict[str, Any]) -> None:
        """
        Load compiled session data from DSL compiler (dict format).

        Compatibility method for SessionState migration.
        Converts dict to CompiledSession and loads it.
        """
        session = CompiledSession.from_dict(data)
        self.load_session(session)

    def set_pending_change(
        self,
        session_data: dict[str, Any],
        timing: str = "bar",
        track_ids: list[str] | None = None,
    ) -> None:
        """
        Queue a pending change (for backward compatibility).
        """
        from typing import cast

        session = CompiledSession.from_dict(session_data)
        self.set_pending(
            session=session,
            timing=cast("ApplyTiming", timing),
            track_ids=track_ids or [],
        )

    def apply_pending_changes(self) -> bool:
        """Apply pending changes (for backward compatibility)"""
        return self.execute_pending()

    def clear_non_specified_track_events(self, specified_ids: list[str]) -> None:
        """Clear events for tracks not in specified list (public API)"""
        self._clear_non_specified_events(specified_ids)

    def activate_scene(self, scene_name: str) -> bool:
        """Activate a scene by name (for backward compatibility)."""
        return self.apply_scene(scene_name)

    def get_scene_names(self) -> list[str]:
        """Get list of available scene names"""
        return list(self.get_effective().scenes.keys())

    def set_track_mute(self, track_id: str, mute: bool) -> bool:
        """
        Set mute state for a track.

        Creates an override with updated mute state.
        """
        eff = self.get_effective()
        if track_id not in eff.tracks:
            return False

        track = eff.tracks[track_id]
        updated_track = Track(
            meta=TrackMeta(
                track_id=track.meta.track_id,
                range_id=track.meta.range_id,
                mute=mute,
                solo=track.meta.solo,
            ),
            params=track.params,
            fx=track.fx,
            track_fx=track.track_fx,
            sends=track.sends,
            modulations=track.modulations,
        )

        override = CompiledSession(tracks={track_id: updated_track})
        self.apply_override(override)
        return True

    def set_track_solo(self, track_id: str, solo: bool) -> bool:
        """
        Set solo state for a track.

        Creates an override with updated solo state.
        """
        eff = self.get_effective()
        if track_id not in eff.tracks:
            return False

        track = eff.tracks[track_id]
        updated_track = Track(
            meta=TrackMeta(
                track_id=track.meta.track_id,
                range_id=track.meta.range_id,
                mute=track.meta.mute,
                solo=solo,
            ),
            params=track.params,
            fx=track.fx,
            track_fx=track.track_fx,
            sends=track.sends,
            modulations=track.modulations,
        )

        override = CompiledSession(tracks={track_id: updated_track})
        self.apply_override(override)
        return True
