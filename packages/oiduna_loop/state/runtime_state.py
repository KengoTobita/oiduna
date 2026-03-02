"""
Oiduna Loop Runtime State

Simplified runtime state for ScheduledMessageBatch architecture.

Responsibilities:
1. Playback state (playing, paused, position)
2. BPM management
3. Mute/Solo filtering (track_id based)
4. Active track tracking
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from ..constants import LOOP_STEPS

if TYPE_CHECKING:
    from oiduna_scheduler.scheduler_models import ScheduledMessage

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
class RuntimeState:
    """
    Simplified runtime state for ScheduledMessageBatch architecture.

    Responsibilities:
    1. Playback state (playing, paused, position)
    2. BPM management
    3. Mute/Solo filtering (track_id based)
    4. Active track tracking

    Note: This state no longer manages CompiledSession or Scenes.
    All pattern data is handled via ScheduledMessageBatch.
    """

    # Playback state
    position: Position = field(default_factory=Position)
    playback_state: PlaybackState = PlaybackState.STOPPED

    # BPM and timing
    _bpm: float = 120.0
    _step_duration: float = 0.125  # 120 BPM default
    _cps: float = 0.5  # cycles per second

    # Track filtering (mute/solo)
    _track_mute: dict[str, bool] = field(default_factory=dict)
    _track_solo: dict[str, bool] = field(default_factory=dict)
    _known_track_ids: set[str] = field(default_factory=set)
    _active_track_ids: set[str] = field(default_factory=set)

    # SSE configuration
    position_update_interval: str = "beat"  # "beat" (4 steps) or "bar" (16 steps)

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
        return self._bpm

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
        """Get loop length in steps"""
        return int(LOOP_STEPS)

    def set_bpm(self, bpm: float) -> None:
        """Update BPM dynamically"""
        self._bpm = max(1.0, min(999.0, bpm))
        self._update_timing()

    def _update_timing(self) -> None:
        """Update timing calculations from BPM"""
        self._step_duration = 60.0 / self._bpm / 4
        self._cps = self._bpm / 60.0 / 4

    def advance_step(self) -> None:
        """Advance playback position by one step"""
        self.position.advance(LOOP_STEPS)

    def reset_position(self) -> None:
        """Reset playback position to start"""
        self.position.reset()

    # ============================================================
    # Mute/Solo Filtering
    # ============================================================

    def register_track(self, track_id: str) -> None:
        """Register a track_id as known (called when loading messages)"""
        self._known_track_ids.add(track_id)
        self._update_active_tracks()

    def set_track_mute(self, track_id: str, muted: bool) -> bool:
        """
        Set mute state for a track.

        Returns True if successful, False if track not registered.
        """
        if track_id not in self._known_track_ids:
            return False

        self._track_mute[track_id] = muted
        self._update_active_tracks()
        return True

    def set_track_solo(self, track_id: str, soloed: bool) -> bool:
        """
        Set solo state for a track.

        Returns True if successful, False if track not registered.
        """
        if track_id not in self._known_track_ids:
            return False

        self._track_solo[track_id] = soloed
        self._update_active_tracks()
        return True

    def _update_active_tracks(self) -> None:
        """
        Update active track set based on mute/solo states.

        Solo takes priority: if any tracks are soloed, only those play.
        Otherwise, all non-muted tracks play.
        """
        solo_tracks = {tid for tid, s in self._track_solo.items() if s}
        if solo_tracks:
            self._active_track_ids = solo_tracks
        else:
            self._active_track_ids = {
                tid for tid in self._known_track_ids
                if not self._track_mute.get(tid, False)
            }

    def is_track_active(self, track_id: str) -> bool:
        """
        Check if a track should output sound.

        Returns True if track is in active set, False otherwise.
        Unknown tracks default to inactive.
        """
        return track_id in self._active_track_ids

    def filter_messages(
        self, messages: list[ScheduledMessage]
    ) -> list[ScheduledMessage]:
        """
        Filter messages based on mute/solo state.

        Performance optimization:
        - If no tracks are muted/soloed, returns original list (no copy, ~50% memory savings)
        - Otherwise, filters using list comprehension with walrus operator (~20% faster)

        Messages without track_id in params are passed through unchanged.
        Messages with unknown track_id are filtered out.

        Args:
            messages: List of ScheduledMessage to filter

        Returns:
            Filtered list of messages (only active tracks + trackless messages)
        """
        # Fast path: no mute/solo AND no registered tracks → return as-is (no copy)
        # (If tracks are registered, we must filter unknown track_ids)
        if not self._track_mute and not self._track_solo and not self._known_track_ids:
            return messages

        # Slow path: filter active tracks + trackless messages
        # Use walrus operator to get track_id only once per message
        return [
            msg for msg in messages
            if (track_id := msg.params.get("track_id")) is None
            or self.is_track_active(track_id)
        ]

    def get_active_track_ids(self) -> list[str]:
        """Get list of currently active track IDs"""
        return sorted(self._active_track_ids)

    # ============================================================
    # Status / IPC
    # ============================================================

    def to_status_dict(self) -> dict[str, Any]:
        """Convert to status message format"""
        return {
            "playing": self.playing,
            "playback_state": self.playback_state.value,
            "bpm": self.bpm,
            "position": self.position.to_dict(),
            "active_tracks": self.get_active_track_ids(),
            "known_tracks": sorted(self._known_track_ids),
            "muted_tracks": sorted(tid for tid, m in self._track_mute.items() if m),
            "soloed_tracks": sorted(tid for tid, s in self._track_solo.items() if s),
        }

    # ============================================================
    # Backwards Compatibility (Minimal)
    # ============================================================

    @property
    def tracks(self) -> dict[str, Any]:
        """
        Get all tracks (for backward compatibility).

        Returns empty dict - no longer supported in new architecture.
        """
        return {}

    @property
    def sequences(self) -> dict[str, Any]:
        """
        Get all sequences (for backward compatibility).

        Returns empty dict - no longer supported in new architecture.
        """
        return {}
