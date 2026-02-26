"""Track models for MARS DSL v5 (SuperDirt).

Represents Layer 2 of the 3-layer data model for SuperDirt tracks.

v5 Changes:
- Added TrackFxParams for tone-shaping effects (filter, distortion, envelope, etc.)
- Added sends field for multi-bus routing
- FxParams retained for backwards compatibility (contains all effects)
- Spatial effects (reverb, delay, leslie) now belong to MixerLineFx
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from oiduna_core.modulation.modulation import Modulation
from .send import Send


@dataclass
class TrackParams:
    """Sound parameters for a SuperDirt track."""

    s: str  # Resolved OSC sound name (e.g., "super808")
    s_path: str = ""  # Original hierarchical path (e.g., "synthdef.drum.super808")
    n: int = 0  # Sample number
    gain: float = 1.0
    pan: float = 0.5
    speed: float = 1.0
    begin: float = 0.0
    end: float = 1.0
    # Voice control
    cut: int | None = None  # Cut group
    legato: float | None = None  # Note length multiplier
    # SynthDef-specific extra parameters (e.g., super808's rate, voice)
    extra_params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        result: dict[str, Any] = {
            "s": self.s,
            "s_path": self.s_path,
            "n": self.n,
            "gain": self.gain,
            "pan": self.pan,
            "speed": self.speed,
            "begin": self.begin,
            "end": self.end,
        }
        if self.cut is not None:
            result["cut"] = self.cut
        if self.legato is not None:
            result["legato"] = self.legato
        if self.extra_params:
            result["extra_params"] = self.extra_params
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TrackParams:
        """Create from dictionary (deserialization)."""
        return cls(
            s=data["s"],
            s_path=data.get("s_path", ""),
            n=data.get("n", 0),
            gain=data.get("gain", 1.0),
            pan=data.get("pan", 0.5),
            speed=data.get("speed", 1.0),
            begin=data.get("begin", 0.0),
            end=data.get("end", 1.0),
            cut=data.get("cut"),
            legato=data.get("legato"),
            extra_params=data.get("extra_params", {}),
        )


@dataclass
class FxParams:
    """Effect parameters for a SuperDirt track."""

    # Filter
    cutoff: float | None = None
    resonance: float | None = None
    hcutoff: float | None = None
    hresonance: float | None = None
    bandf: float | None = None
    bandq: float | None = None

    # Reverb
    room: float | None = None
    size: float | None = None
    dry: float | None = None

    # Delay
    delay_send: float | None = None
    delay_time: float | None = None
    delay_feedback: float | None = None

    # Distortion
    shape: float | None = None
    crush: float | None = None
    coarse: float | None = None

    # Envelope
    attack: float | None = None
    hold: float | None = None
    release: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary (only non-None values)."""
        return {k: v for k, v in self.__dict__.items() if v is not None}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FxParams:
        """Create from dictionary (deserialization)."""
        valid_keys = set(cls.__dataclass_fields__.keys())
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


@dataclass
class TrackFxParams:
    """Tone-shaping effect parameters for a Track (v5).

    These effects shape the character of individual sounds and are
    applied per-track, not shared across tracks.

    Note: Spatial effects (reverb, delay, leslie) belong to MixerLineFx.
    """

    # Filter
    cutoff: float | None = None  # Lowpass cutoff (20-20000 Hz)
    resonance: float | None = None  # Lowpass resonance (0-1)
    hcutoff: float | None = None  # Highpass cutoff (20-20000 Hz)
    hresonance: float | None = None  # Highpass resonance (0-1)
    bandf: float | None = None  # Bandpass center frequency
    bandq: float | None = None  # Bandpass Q
    vowel: str | None = None  # Vowel formant filter (a, e, i, o, u)

    # Distortion
    shape: float | None = None  # Waveshaping amount (0-1)
    crush: float | None = None  # Bit depth (1-24, lower = rougher)
    coarse: float | None = None  # Sample rate reduction (1-64)
    krush: float | None = None  # Sonic Pi krush distortion
    kcutoff: float | None = None  # Krush filter cutoff (Hz)
    triode: float | None = None  # Triode tube distortion

    # Envelope
    attack: float | None = None  # Attack time (seconds)
    hold: float | None = None  # Hold time (seconds)
    release: float | None = None  # Release time (seconds)

    # Modulation (tone-shaping)
    tremolo_rate: float | None = None  # Tremolo speed
    tremolo_depth: float | None = None  # Tremolo amount (0-1)
    phaser_rate: float | None = None  # Phaser speed
    phaser_depth: float | None = None  # Phaser amount (0-1)

    # Pitch
    detune: float | None = None  # Detune amount
    accelerate: float | None = None  # Pitch acceleration over time
    psrate: float | None = None  # Pitch shift rate
    psdisp: float | None = None  # Pitch shift dispersion

    # Spectral/FFT effects
    freeze: float | None = None  # FFT freeze (0-1)
    smear: float | None = None  # Spectral smearing
    binshift: float | None = None  # FFT bin shifting
    comb: float | None = None  # Spectral comb filter
    scram: float | None = None  # Spectral scramble
    hbrick: float | None = None  # Spectral high-pass brick wall
    lbrick: float | None = None  # Spectral low-pass brick wall
    enhance: float | None = None  # Spectral enhancement
    tsdelay: float | None = None  # Spectral delay time
    xsdelay: float | None = None  # Spectral delay mix

    # Ring modulation
    ring: float | None = None  # Ring modulation amount
    ringf: float | None = None  # Ring modulation frequency (Hz)
    ringdf: float | None = None  # Ring frequency slide (Hz)

    # Additional effects
    squiz: float | None = None  # Squiz pitch ratio
    waveloss: float | None = None  # Wave segment drop percentage
    octer: float | None = None  # Octave-up harmonics
    octersub: float | None = None  # Half-frequency harmonics
    octersubsub: float | None = None  # Quarter-frequency harmonics
    fshift: float | None = None  # Frequency shift (Hz)
    fshiftnote: float | None = None  # Shift as fraction of note freq
    fshiftphase: float | None = None  # Shift phase (radians)
    djf: float | None = None  # DJ filter position

    # Compressor
    cthresh: float | None = None  # Compression threshold
    cratio: float | None = None  # Compression ratio
    cattack: float | None = None  # Compressor attack time
    crelease: float | None = None  # Compressor release time
    cgain: float | None = None  # Compressor output gain
    cknee: float | None = None  # Soft knee amount

    # Pan extras
    panspread: float | None = None  # Stereo spread

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary (only non-None values)."""
        return {k: v for k, v in self.__dict__.items() if v is not None}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TrackFxParams:
        """Create from dictionary (deserialization)."""
        valid_keys = set(cls.__dataclass_fields__.keys())
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


@dataclass
class TrackMeta:
    """Track metadata for SuperDirt."""

    track_id: str
    range_id: int = 2
    mute: bool = False
    solo: bool = False


@dataclass
class Track:
    """SuperDirt track definition.

    Represents Layer 2 of the 3-layer data model.
    Contains sound parameters, effects, modulations, and sends.

    v5 Changes:
    - Added sends for multi-bus routing to MixerLines
    - Added track_fx for tone-shaping effects (separate from spatial fx)
    - fx field retained for backwards compatibility
    """

    meta: TrackMeta
    params: TrackParams
    fx: FxParams = field(default_factory=FxParams)
    track_fx: TrackFxParams = field(default_factory=TrackFxParams)
    sends: tuple[Send, ...] = field(default_factory=tuple)
    modulations: dict[str, Modulation] = field(default_factory=dict)

    @property
    def id(self) -> str:
        """Get track ID."""
        return self.meta.track_id

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        result: dict[str, Any] = {
            "meta": {
                "track_id": self.meta.track_id,
                "range_id": self.meta.range_id,
                "mute": self.meta.mute,
                "solo": self.meta.solo,
            },
            "params": self.params.to_dict(),
            "fx": self.fx.to_dict(),
            "track_fx": self.track_fx.to_dict(),
            "modulations": {k: v.to_dict() for k, v in self.modulations.items()},
        }
        if self.sends:
            result["sends"] = [s.to_dict() for s in self.sends]
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Track:
        """Create from dictionary (deserialization)."""
        meta_data = data["meta"]
        params_data = data["params"]

        # Parse sends
        sends_data = data.get("sends", [])
        sends = tuple(Send.from_dict(s) for s in sends_data)

        return cls(
            meta=TrackMeta(
                track_id=meta_data["track_id"],
                range_id=meta_data.get("range_id", 2),
                mute=meta_data.get("mute", False),
                solo=meta_data.get("solo", False),
            ),
            params=TrackParams.from_dict(params_data),
            fx=FxParams.from_dict(data.get("fx", {})),
            track_fx=TrackFxParams.from_dict(data.get("track_fx", {})),
            sends=sends,
            modulations={
                k: Modulation.from_dict(v)
                for k, v in data.get("modulations", {}).items()
            },
        )
