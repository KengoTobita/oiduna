"""
Test Helpers for v5 Migration

Provides helper functions to create RuntimeState instances with v5 models
for testing purposes.
"""

from __future__ import annotations

from typing import Any

from oiduna_core.models.environment import Environment
from oiduna_core.models.sequence import Event, EventSequence
from oiduna_core.models.session import CompiledSession
from oiduna_core.models.track import FxParams, Track, TrackMeta, TrackParams
from oiduna_core.models.track_midi import TrackMidi

from ..state import RuntimeState


def create_test_runtime_state(
    bpm: float = 120.0,
    tracks: dict[str, dict[str, Any]] | None = None,
    tracks_midi: dict[str, dict[str, Any]] | None = None,
    sequences: dict[str, list[dict[str, Any]]] | None = None,
) -> RuntimeState:
    """
    Create a RuntimeState with test data.

    Args:
        bpm: BPM value
        tracks: Dict of track_id -> track config dict
        tracks_midi: Dict of track_id -> MIDI track config dict
        sequences: Dict of track_id -> list of event dicts

    Returns:
        Configured RuntimeState
    """
    state = RuntimeState()

    env = Environment(bpm=bpm)
    v5_tracks: dict[str, Track] = {}
    v5_tracks_midi: dict[str, TrackMidi] = {}
    v5_sequences: dict[str, EventSequence] = {}

    # Build tracks
    if tracks:
        for track_id, track_data in tracks.items():
            sound_params = track_data.get("sound_params", {})
            fx_params_dict = track_data.get("fx_params", {})

            meta = TrackMeta(
                track_id=track_id,
                mute=track_data.get("mute", False),
                solo=track_data.get("solo", False),
            )
            params = TrackParams(
                s=sound_params.get("s", ""),
                n=sound_params.get("n", 0),
                gain=sound_params.get("gain", 1.0),
                pan=sound_params.get("pan", 0.5),
                speed=sound_params.get("speed", 1.0),
                begin=sound_params.get("begin", 0.0),
                end=sound_params.get("end", 1.0),
                orbit=sound_params.get("orbit", 0),
                cut=sound_params.get("cut"),
                legato=sound_params.get("legato"),
            )
            fx = FxParams(
                room=fx_params_dict.get("room"),
                size=fx_params_dict.get("size"),
                delay_send=fx_params_dict.get("delaySend"),
                delay_time=fx_params_dict.get("delaytime"),
                delay_feedback=fx_params_dict.get("delayfeedback"),
                cutoff=fx_params_dict.get("cutoff"),
                resonance=fx_params_dict.get("resonance"),
            )
            v5_tracks[track_id] = Track(meta=meta, params=params, fx=fx)

    # Build MIDI tracks
    if tracks_midi:
        for track_id, track_data in tracks_midi.items():
            v5_tracks_midi[track_id] = TrackMidi(
                track_id=track_id,
                channel=track_data.get("channel", 0),
                velocity=track_data.get("velocity", 127),
                transpose=track_data.get("transpose", 0),
                mute=track_data.get("mute", False),
                solo=track_data.get("solo", False),
            )

    # Build sequences
    if sequences:
        for track_id, events_data in sequences.items():
            events = [
                Event(
                    step=e.get("step", 0),
                    velocity=e.get("velocity", 1.0),
                    note=e.get("note"),
                    gate=e.get("gate", 1.0),
                )
                for e in events_data
            ]
            v5_sequences[track_id] = EventSequence.from_events(
                track_id=track_id, events=events
            )

    session = CompiledSession(
        environment=env,
        tracks=v5_tracks,
        tracks_midi=v5_tracks_midi,
        sequences=v5_sequences,
    )
    state.load_session(session)
    return state


def create_superdirt_test_state(
    track_id: str,
    sound: str,
    events: list[dict[str, Any]],
    fx_params: dict[str, Any] | None = None,
    mute: bool = False,
    solo: bool = False,
    bpm: float = 120.0,
) -> RuntimeState:
    """
    Create a RuntimeState with a single SuperDirt track.

    Convenience function for simple test cases.
    """
    return create_test_runtime_state(
        bpm=bpm,
        tracks={
            track_id: {
                "sound_params": {"s": sound},
                "fx_params": fx_params or {},
                "mute": mute,
                "solo": solo,
            }
        },
        sequences={track_id: events},
    )


def create_midi_test_state(
    track_id: str,
    channel: int,
    events: list[dict[str, Any]],
    velocity: int = 127,
    transpose: int = 0,
    mute: bool = False,
    solo: bool = False,
    bpm: float = 120.0,
) -> RuntimeState:
    """
    Create a RuntimeState with a single MIDI track.

    Convenience function for simple test cases.
    """
    return create_test_runtime_state(
        bpm=bpm,
        tracks_midi={
            track_id: {
                "channel": channel,
                "velocity": velocity,
                "transpose": transpose,
                "mute": mute,
                "solo": solo,
            }
        },
        sequences={track_id: events},
    )
