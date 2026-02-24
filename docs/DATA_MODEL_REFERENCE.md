# Oiduna Data Model Reference

**Version**: 1.0
**Last Updated**: 2026-02-24
**Status**: Stable

Complete reference for all Oiduna IR (Intermediate Representation) models.

---

## Table of Contents

1. [Overview](#overview)
2. [CompiledSession](#compiledsession)
3. [Environment Layer](#environment-layer)
4. [Configuration Layer](#configuration-layer)
5. [Pattern Layer](#pattern-layer)
6. [Control Layer](#control-layer)
7. [Modulation](#modulation)
8. [Serialization](#serialization)
9. [JSON Examples](#json-examples)

---

## Overview

### Model Hierarchy

```
CompiledSession (Top-level)
│
├── Environment Layer
│   ├── Environment
│   └── Chord
│
├── Configuration Layer
│   ├── Track (SuperDirt)
│   │   ├── TrackMeta
│   │   ├── TrackParams
│   │   ├── FxParams (legacy)
│   │   ├── TrackFxParams (v5)
│   │   └── Send
│   ├── TrackMidi
│   └── MixerLine
│       ├── MixerLineDynamics
│       └── MixerLineFx
│
├── Pattern Layer
│   ├── EventSequence
│   └── Event
│
└── Control Layer
    ├── Scene
    └── ApplyCommand
```

### Design Principles

All models follow these principles:

1. **Immutability** - Most models use `frozen=True` (except mutable containers)
2. **Type Safety** - Full Python 3.13 type hints + mypy validation
3. **Serializable** - All models have `to_dict()` / `from_dict()` methods
4. **Slots** - Performance-critical models use `slots=True`

### File Locations

```
oiduna/packages/oiduna_core/ir/
├── session.py          # CompiledSession, ApplyCommand
├── environment.py      # Environment, Chord
├── track.py            # Track, TrackParams, FxParams, TrackFxParams
├── track_midi.py       # TrackMidi
├── mixer_line.py       # MixerLine, MixerLineDynamics, MixerLineFx
├── send.py             # Send
├── sequence.py         # EventSequence, Event
└── scene.py            # Scene
```

---

## CompiledSession

### Definition

```python
@dataclass
class CompiledSession:
    environment: Environment = field(default_factory=Environment)
    tracks: dict[str, Track] = field(default_factory=dict)
    tracks_midi: dict[str, TrackMidi] = field(default_factory=dict)
    mixer_lines: dict[str, MixerLine] = field(default_factory=dict)
    sequences: dict[str, EventSequence] = field(default_factory=dict)
    scenes: dict[str, Scene] = field(default_factory=dict)
    apply: ApplyCommand | None = None
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `environment` | `Environment` | Global playback settings (BPM, swing, etc.) |
| `tracks` | `dict[str, Track]` | SuperDirt audio tracks (key = track_id) |
| `tracks_midi` | `dict[str, TrackMidi]` | MIDI output tracks (key = track_id) |
| `mixer_lines` | `dict[str, MixerLine]` | Mixer buses and master section |
| `sequences` | `dict[str, EventSequence]` | Event sequences (key = track_id) |
| `scenes` | `dict[str, Scene]` | Snapshots for scene switching |
| `apply` | `ApplyCommand \| None` | Timing control for pattern application |

### Key Relationships

```
tracks["kick"]      ←→ sequences["kick"]      # Same track_id
tracks["snare"]     ←→ sequences["snare"]
mixer_lines["drums"].include = ["kick", "snare"]  # Routing
```

### Validation Rules

- Track IDs in `tracks` should match keys in `sequences`
- Track IDs in `mixer_lines.include` must exist in `tracks`
- `apply.track_ids` must exist in `tracks` (if specified)

### JSON Schema

```json
{
  "environment": { "bpm": 120.0, ... },
  "tracks": {
    "track_id_1": { ... },
    "track_id_2": { ... }
  },
  "tracks_midi": {
    "midi_track_1": { ... }
  },
  "mixer_lines": {
    "master": { ... }
  },
  "sequences": {
    "track_id_1": { "events": [...] },
    "track_id_2": { "events": [...] }
  },
  "scenes": {
    "intro": { ... },
    "verse": { ... }
  },
  "apply": {
    "timing": "bar",
    "track_ids": [],
    "scene_name": null
  }
}
```

---

## Environment Layer

### Environment

**Purpose**: Global settings shared by all tracks

```python
@dataclass
class Environment:
    bpm: float = 120.0
    scale: str = "C_major"        # 🚫 Deprecated in v1.1
    default_gate: float = 1.0
    swing: float = 0.0
    loop_steps: int = 256         # Fixed, never changes
    chords: list[Chord] = field(default_factory=list)  # 🚫 Deprecated in v1.1
```

#### Fields

| Field | Type | Range | Default | Description |
|-------|------|-------|---------|-------------|
| `bpm` | `float` | > 0 | 120.0 | Beats per minute |
| `scale` | `str` | - | "C_major" | Musical scale (deprecated v1.1) |
| `default_gate` | `float` | 0.0-1.0 | 1.0 | Default note length ratio |
| `swing` | `float` | 0.0-1.0 | 0.0 | Swing amount (0 = straight, 1 = max swing) |
| `loop_steps` | `int` | 256 | 256 | **Fixed**, never changes |
| `chords` | `list[Chord]` | - | [] | Chord progression (deprecated v1.1) |

#### BPM Timing Calculations

```python
step_duration_ms = 60000 / bpm / 4  # Duration of one step
# Example @ 120 BPM:
# step_duration = 60000 / 120 / 4 = 125ms
# 256 steps = 32 seconds total loop
```

#### Deprecation Notices

**v1.1 Changes**:
- `scale` field will be removed - music theory belongs in Distribution
- `chords` field will be removed - music theory belongs in Distribution

**Rationale**: Oiduna receives pre-resolved MIDI note numbers. Music theory processing happens in Distribution layer.

#### JSON Example

```json
{
  "bpm": 140.0,
  "default_gate": 0.9,
  "swing": 0.1,
  "loop_steps": 256
}
```

### Chord

**Purpose**: Chord definition for chord progression (deprecated v1.1)

```python
@dataclass
class Chord:
    name: str
    length: int | None = None  # None = equal division
```

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Chord name (e.g., "Cmaj7", "Dm7") |
| `length` | `int \| None` | Duration in steps (None = equal split) |

**Note**: This model is deprecated in v1.1. Use Distribution-level chord tracking instead.

---

## Configuration Layer

### Track (SuperDirt)

**Purpose**: Audio track configuration for SuperDirt output

```python
@dataclass
class Track:
    meta: TrackMeta
    params: TrackParams
    fx: FxParams                            # Legacy effects
    track_fx: TrackFxParams                 # v5 tone-shaping effects
    sends: tuple[Send, ...] = field(default_factory=tuple)
    modulations: dict[str, Modulation] = field(default_factory=dict)
```

#### Signal Flow

```
Event → TrackParams (s, gain, pan)
     → TrackFxParams (filter, distortion, envelope)
     → Sends → MixerLine
              → MixerLineFx (reverb, delay, leslie)
              → Output
```

### TrackMeta

**Purpose**: Track identification and state

```python
@dataclass
class TrackMeta:
    track_id: str
    range_id: int = 2
    mute: bool = False
    solo: bool = False
```

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `track_id` | `str` | Unique track identifier |
| `range_id` | `int` | Range identifier (unused, legacy) |
| `mute` | `bool` | Track muted state |
| `solo` | `bool` | Track solo state |

#### JSON Example

```json
{
  "track_id": "kick",
  "range_id": 2,
  "mute": false,
  "solo": false
}
```

### TrackParams

**Purpose**: Sound generation parameters

```python
@dataclass
class TrackParams:
    s: str                       # Sound name (OSC parameter)
    s_path: str = ""            # Hierarchical path (e.g., "synthdef.drum.bd")
    n: int = 0                  # Sample number
    gain: float = 1.0
    pan: float = 0.5
    speed: float = 1.0
    begin: float = 0.0
    end: float = 1.0
    orbit: int = 0
    cut: int | None = None
    legato: float | None = None
    extra_params: dict[str, Any] = field(default_factory=dict)
```

#### Fields

| Field | Type | Range | Default | Description |
|-------|------|-------|---------|-------------|
| `s` | `str` | - | required | SuperDirt sound name (e.g., "bd", "super808") |
| `s_path` | `str` | - | "" | Original hierarchical path |
| `n` | `int` | ≥ 0 | 0 | Sample variation number |
| `gain` | `float` | 0.0-1.0+ | 1.0 | Volume level |
| `pan` | `float` | 0.0-1.0 | 0.5 | Stereo position (0=left, 0.5=center, 1=right) |
| `speed` | `float` | > 0 | 1.0 | Playback speed (1=normal, 2=double, 0.5=half) |
| `begin` | `float` | 0.0-1.0 | 0.0 | Sample start position |
| `end` | `float` | 0.0-1.0 | 1.0 | Sample end position |
| `orbit` | `int` | 0-11 | 0 | SuperDirt orbit (output channel) |
| `cut` | `int \| None` | - | None | Cut group (mutes other notes in same group) |
| `legato` | `float \| None` | > 0 | None | Note length multiplier |
| `extra_params` | `dict` | - | {} | SynthDef-specific parameters |

#### JSON Example

```json
{
  "s": "bd",
  "s_path": "samples.acoustic.bd",
  "n": 0,
  "gain": 0.8,
  "pan": 0.5,
  "speed": 1.0,
  "begin": 0.0,
  "end": 1.0,
  "orbit": 0,
  "cut": null,
  "legato": null,
  "extra_params": {}
}
```

### FxParams (Legacy)

**Purpose**: Backwards-compatible effects container

```python
@dataclass
class FxParams:
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
```

**Note**: In v5, prefer `TrackFxParams` for tone-shaping and `MixerLineFx` for spatial effects.

### TrackFxParams (v5)

**Purpose**: Tone-shaping effects applied per-track

```python
@dataclass
class TrackFxParams:
    # Filter
    cutoff: float | None = None      # Lowpass cutoff (20-20000 Hz)
    resonance: float | None = None   # Lowpass resonance (0-1)
    hcutoff: float | None = None     # Highpass cutoff (20-20000 Hz)
    hresonance: float | None = None  # Highpass resonance (0-1)
    bandf: float | None = None       # Bandpass center frequency
    bandq: float | None = None       # Bandpass Q
    vowel: str | None = None         # Vowel formant filter (a, e, i, o, u)

    # Distortion
    shape: float | None = None       # Waveshaping (0-1)
    crush: float | None = None       # Bit depth (1-24)
    coarse: float | None = None      # Sample rate reduction (1-64)
    krush: float | None = None       # Sonic Pi krush
    kcutoff: float | None = None     # Krush filter cutoff
    triode: float | None = None      # Triode tube distortion

    # Envelope
    attack: float | None = None      # Attack time (seconds)
    hold: float | None = None        # Hold time (seconds)
    decay: float | None = None       # Decay time (seconds)
    release: float | None = None     # Release time (seconds)

    # Ring modulation
    ring: float | None = None        # Ring mod amount (0-1)
    ringf: float | None = None       # Ring mod frequency (Hz)
    ringdf: float | None = None      # Ring mod detuning (Hz)
```

#### Effect Categories

**Filters**:
- `cutoff`, `resonance` - Lowpass (darkens sound)
- `hcutoff`, `hresonance` - Highpass (removes bass)
- `bandf`, `bandq` - Bandpass (telephone effect)
- `vowel` - Formant filter ("a", "e", "i", "o", "u")

**Distortion**:
- `shape` - Waveshaping distortion (analog warmth)
- `crush` - Bitcrusher (digital grit)
- `coarse` - Sample rate reduction (lo-fi)
- `triode` - Tube distortion

**Envelope**:
- `attack` - Fade-in time
- `hold` - Sustain time
- `decay` - Post-peak decay
- `release` - Fade-out time

#### JSON Example

```json
{
  "cutoff": 2000.0,
  "resonance": 0.3,
  "shape": 0.5,
  "attack": 0.01,
  "release": 0.2
}
```

### Send

**Purpose**: Route track to mixer line

```python
@dataclass(frozen=True)
class Send:
    mixer_line: str     # Target mixer line name
    gain: float = 1.0   # Send level (0.0-1.0)
    pan: float = 0.5    # Pre-mixer pan
```

#### Fields

| Field | Type | Range | Default | Description |
|-------|------|-------|---------|-------------|
| `mixer_line` | `str` | - | required | Target mixer line name |
| `gain` | `float` | 0.0-1.0+ | 1.0 | Send level |
| `pan` | `float` | 0.0-1.0 | 0.5 | Pre-mixer pan |

#### JSON Example

```json
{
  "mixer_line": "drums_bus",
  "gain": 0.8,
  "pan": 0.5
}
```

### TrackMidi

**Purpose**: MIDI output track configuration

```python
@dataclass
class TrackMidi:
    track_id: str
    channel: int                                  # 0-15
    velocity: int = 127
    transpose: int = 0
    mute: bool = False
    solo: bool = False
    cc_modulations: dict[int, Modulation] = field(default_factory=dict)
    pitch_bend_modulation: Modulation | None = None
    aftertouch_modulation: Modulation | None = None
    velocity_modulation: Modulation | None = None
```

#### Fields

| Field | Type | Range | Default | Description |
|-------|------|-------|---------|-------------|
| `track_id` | `str` | - | required | Unique track identifier |
| `channel` | `int` | 0-15 | required | MIDI channel |
| `velocity` | `int` | 0-127 | 127 | Default note velocity |
| `transpose` | `int` | -127 to 127 | 0 | Semitone transposition |
| `mute` | `bool` | - | False | Mute state |
| `solo` | `bool` | - | False | Solo state |
| `cc_modulations` | `dict[int, Modulation]` | - | {} | CC# → Modulation mapping |
| `pitch_bend_modulation` | `Modulation \| None` | - | None | Pitch bend modulation |
| `aftertouch_modulation` | `Modulation \| None` | - | None | Aftertouch modulation |
| `velocity_modulation` | `Modulation \| None` | - | None | Velocity modulation |

#### JSON Example

```json
{
  "track_id": "midi_synth",
  "channel": 0,
  "velocity": 100,
  "transpose": 12,
  "mute": false,
  "solo": false,
  "cc_modulations": {},
  "pitch_bend_modulation": null,
  "aftertouch_modulation": null,
  "velocity_modulation": null
}
```

### MixerLine

**Purpose**: Mixer bus with routing and effects

```python
@dataclass(frozen=True)
class MixerLine:
    name: str
    include: tuple[str, ...] = field(default_factory=tuple)
    volume: float = 1.0
    pan: float = 0.5
    mute: bool = False
    solo: bool = False
    output: int = 0
    dynamics: MixerLineDynamics = field(default_factory=MixerLineDynamics)
    fx: MixerLineFx = field(default_factory=MixerLineFx)
```

#### Fields

| Field | Type | Range | Default | Description |
|-------|------|-------|---------|-------------|
| `name` | `str` | - | required | Mixer line identifier |
| `include` | `tuple[str, ...]` | - | () | Track IDs included in this line |
| `volume` | `float` | 0.0-1.0+ | 1.0 | Line volume |
| `pan` | `float` | 0.0-1.0 | 0.5 | Stereo pan |
| `mute` | `bool` | - | False | Mute state |
| `solo` | `bool` | - | False | Solo state |
| `output` | `int` | 0-11 | 0 | Output orbit |
| `dynamics` | `MixerLineDynamics` | - | (default) | Dynamics processing |
| `fx` | `MixerLineFx` | - | (default) | Spatial effects |

### MixerLineDynamics

**Purpose**: Dynamics processing (limiter, compressor)

```python
@dataclass(frozen=True)
class MixerLineDynamics:
    limiter_threshold: float = 0.99
    limiter_release: float = 0.01
    compressor_threshold: float = 0.5
    compressor_ratio: float = 4.0
    compressor_attack: float = 0.003
    compressor_release: float = 0.09
    compressor_knee: float = 4.0
    compressor_makeup: float = 1.0
```

### MixerLineFx

**Purpose**: Shared spatial effects

```python
@dataclass(frozen=True)
class MixerLineFx:
    # Reverb
    reverb_send: float | None = None
    reverb_room: float | None = None
    reverb_size: float | None = None
    reverb_dry: float | None = None

    # Delay
    delay_send: float | None = None
    delay_time: float | None = None
    delay_feedback: float | None = None

    # Leslie rotary speaker
    leslie_send: float | None = None
    leslie_rate: float | None = None
    leslie_size: float | None = None
```

#### JSON Example (MixerLine)

```json
{
  "name": "drums_bus",
  "include": ["kick", "snare", "hihat"],
  "volume": 0.9,
  "pan": 0.5,
  "mute": false,
  "solo": false,
  "output": 0,
  "dynamics": {
    "limiter_threshold": 0.99,
    "compressor_threshold": 0.5,
    "compressor_ratio": 4.0
  },
  "fx": {
    "reverb_send": 0.3,
    "reverb_room": 0.8,
    "delay_send": 0.2,
    "delay_time": 0.375,
    "delay_feedback": 0.4
  }
}
```

---

## Pattern Layer

### EventSequence

**Purpose**: Time-indexed event collection with O(1) lookup

```python
@dataclass
class EventSequence:
    track_id: str
    _events: tuple[Event, ...] = field(default_factory=tuple)
    _step_index: dict[int, list[int]] = field(default_factory=dict, repr=False)
```

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `track_id` | `str` | Associated track identifier |
| `_events` | `tuple[Event, ...]` | Immutable event tuple |
| `_step_index` | `dict[int, list[int]]` | Step → event indices map (O(1)) |

#### Step Index Design

```python
# Example events
events = [
    Event(step=0, velocity=1.0),   # Index 0
    Event(step=0, velocity=0.8),   # Index 1 (two events at step 0)
    Event(step=4, velocity=1.0),   # Index 2
    Event(step=8, velocity=0.9),   # Index 3
]

# Built index
_step_index = {
    0: [0, 1],  # Two events at step 0
    4: [2],     # One event at step 4
    8: [3],     # One event at step 8
}

# O(1) lookup during playback
current_step = 0
event_indices = sequence._step_index.get(0, [])  # [0, 1]
for idx in event_indices:
    event = sequence._events[idx]
    # Process event
```

#### Methods

```python
@classmethod
def from_events(cls, track_id: str, events: list[Event]) -> EventSequence
    """Create EventSequence from event list (builds index automatically)."""

def get_events_at(self, step: int) -> list[Event]
    """Get events at specific step (O(1))."""

def has_events_at(self, step: int) -> bool
    """Check if events exist at step."""

@property
def steps_with_events(self) -> list[int]
    """Get sorted list of steps that have events."""
```

#### JSON Example

```json
{
  "track_id": "kick",
  "events": [
    {"step": 0, "velocity": 1.0, "gate": 1.0},
    {"step": 4, "velocity": 1.0, "gate": 1.0},
    {"step": 8, "velocity": 1.0, "gate": 1.0}
  ]
}
```

### Event

**Purpose**: Single trigger in a pattern

```python
@dataclass(frozen=True, slots=True)
class Event:
    step: int                    # 0-255
    velocity: float = 1.0        # 0.0-1.0
    note: int | None = None      # MIDI note number
    gate: float = 1.0            # Gate length ratio
    offset_ms: float = 0.0       # NEW in v1.0: micro-timing
```

#### Fields

| Field | Type | Range | Default | Description |
|-------|------|-------|---------|-------------|
| `step` | `int` | 0-255 | required | Position in 256-step loop |
| `velocity` | `float` | 0.0-1.0 | 1.0 | Note intensity |
| `note` | `int \| None` | 0-127 | None | MIDI note number (None for drums) |
| `gate` | `float` | 0.0-1.0+ | 1.0 | Note length ratio (1.0 = full step) |
| `offset_ms` | `float` | ±∞ | 0.0 | Micro-timing offset (ms) |

#### Offset Micro-timing (v1.0)

**Purpose**: Sub-step timing precision for triplets, swing, flams, etc.

**Value Range**:
- Theoretical: Any float
- Recommended: -62.5 to +62.5 (±half step @ 120 BPM)
- Practical: -125 to +125 (±full step @ 120 BPM)

**Calculation**:
```python
base_time = step * step_duration
actual_time = base_time + (offset_ms / 1000.0)
```

**Use Cases**:

1. **Triplets** (8th note triplets):
```python
triplet_interval = (60000 / bpm) / 3  # 166.67ms @ 120 BPM
events = [
    Event(step=0, offset_ms=0.0),       # 1st triplet
    Event(step=0, offset_ms=166.67),    # 2nd triplet
    Event(step=0, offset_ms=333.33),    # 3rd triplet
]
```

2. **Swing**:
```python
swing_ms = 20.0
events = [
    Event(step=0, offset_ms=0.0),       # On-beat
    Event(step=1, offset_ms=swing_ms),  # Delayed (swung)
    Event(step=2, offset_ms=0.0),       # On-beat
    Event(step=3, offset_ms=swing_ms),  # Delayed (swung)
]
```

3. **Flam** (ghost note + main):
```python
events = [
    Event(step=0, offset_ms=-5.0, velocity=0.3),  # Ghost (5ms early)
    Event(step=0, offset_ms=0.0, velocity=1.0),   # Main
]
```

#### JSON Example

```json
{
  "step": 0,
  "velocity": 1.0,
  "note": 60,
  "gate": 0.8,
  "offset_ms": 0.0
}
```

---

## Control Layer

### Scene

**Purpose**: Snapshot of session state for scene switching

```python
@dataclass(frozen=True)
class Scene:
    name: str
    environment: Environment | None = None
    tracks: dict[str, Track] = field(default_factory=dict)
    tracks_midi: dict[str, TrackMidi] = field(default_factory=dict)
    sequences: dict[str, EventSequence] = field(default_factory=dict)
    mixer_lines: dict[str, MixerLine] = field(default_factory=dict)
```

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Scene identifier |
| `environment` | `Environment \| None` | Optional environment override |
| `tracks` | `dict[str, Track]` | Track snapshots |
| `tracks_midi` | `dict[str, TrackMidi]` | MIDI track snapshots |
| `sequences` | `dict[str, EventSequence]` | Pattern snapshots |
| `mixer_lines` | `dict[str, MixerLine]` | Mixer snapshots |

#### Usage Pattern

```python
# Define scenes
scenes = {
    "intro": Scene(
        name="intro",
        tracks={"kick": Track(...), "hihat": Track(...)},
        sequences={"kick": EventSequence(...), "hihat": EventSequence(...)}
    ),
    "verse": Scene(
        name="verse",
        tracks={"kick": Track(...), "snare": Track(...), "hihat": Track(...)},
        sequences={...}
    ),
}

# Switch scene via API
POST /playback/scenes/verse
```

#### JSON Example

```json
{
  "name": "intro",
  "environment": null,
  "tracks": {
    "kick": { ... }
  },
  "tracks_midi": {},
  "sequences": {
    "kick": { ... }
  },
  "mixer_lines": {}
}
```

### ApplyCommand

**Purpose**: Control when and how to apply session changes

```python
@dataclass
class ApplyCommand:
    timing: Literal["now", "beat", "bar", "seq"]
    track_ids: list[str] = field(default_factory=list)
    scene_name: str | None = None
```

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `timing` | `"now" \| "beat" \| "bar" \| "seq"` | When to apply changes |
| `track_ids` | `list[str]` | Which tracks to update (empty = all) |
| `scene_name` | `str \| None` | Scene to activate (if applicable) |

#### Timing Values

| Value | Meaning |
|-------|---------|
| `"now"` | Apply immediately |
| `"beat"` | Apply at next beat boundary (step % 4 == 0) |
| `"bar"` | Apply at next bar boundary (step % 16 == 0) |
| `"seq"` | Apply at sequence start (step == 0) |

#### JSON Example

```json
{
  "timing": "bar",
  "track_ids": ["kick", "snare"],
  "scene_name": null
}
```

---

## Modulation

### Modulation

**Purpose**: Parameter automation over time

```python
@dataclass
class Modulation:
    signal: SignalExpr
    buffer: StepBuffer
    param_name: str
    min_value: float
    max_value: float
```

**Note**: Full modulation system documentation is beyond scope of this reference. See `oiduna_core/modulation/` for implementation details.

---

## Serialization

### JSON Serialization

All models implement:

```python
def to_dict(self) -> dict[str, Any]
    """Convert to JSON-serializable dictionary."""

@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
    """Deserialize from dictionary."""
```

### Serialization Rules

1. **None values** - Omitted from output (compact representation)
2. **Default values** - Included for clarity
3. **Nested models** - Recursively serialized
4. **Tuples** - Serialized as JSON arrays
5. **Immutable** - Source models never modified

### Example Round-trip

```python
# Serialize
session = CompiledSession(...)
json_dict = session.to_dict()
json_str = json.dumps(json_dict)

# Deserialize
loaded_dict = json.loads(json_str)
restored = CompiledSession.from_dict(loaded_dict)

# Immutability preserved
assert session.environment.bpm == restored.environment.bpm
```

---

## JSON Examples

### Minimal Session

```json
{
  "environment": {
    "bpm": 120.0,
    "default_gate": 1.0,
    "swing": 0.0,
    "loop_steps": 256
  },
  "tracks": {
    "kick": {
      "meta": {"track_id": "kick", "mute": false, "solo": false},
      "params": {"s": "bd", "gain": 1.0, "pan": 0.5, "orbit": 0},
      "fx": {},
      "track_fx": {},
      "sends": []
    }
  },
  "tracks_midi": {},
  "mixer_lines": {},
  "sequences": {
    "kick": {
      "track_id": "kick",
      "events": [
        {"step": 0, "velocity": 1.0, "gate": 1.0},
        {"step": 4, "velocity": 1.0, "gate": 1.0},
        {"step": 8, "velocity": 1.0, "gate": 1.0},
        {"step": 12, "velocity": 1.0, "gate": 1.0}
      ]
    }
  },
  "scenes": {},
  "apply": {
    "timing": "bar",
    "track_ids": [],
    "scene_name": null
  }
}
```

### Complex Session with Mixer

```json
{
  "environment": {"bpm": 140.0, "loop_steps": 256},
  "tracks": {
    "kick": {
      "meta": {"track_id": "kick", "mute": false},
      "params": {"s": "bd", "gain": 0.9, "orbit": 0},
      "track_fx": {"cutoff": 200.0, "attack": 0.01},
      "sends": [
        {"mixer_line": "drums_bus", "gain": 1.0, "pan": 0.5}
      ]
    },
    "snare": {
      "meta": {"track_id": "snare", "mute": false},
      "params": {"s": "sd", "gain": 0.8, "orbit": 0},
      "track_fx": {},
      "sends": [
        {"mixer_line": "drums_bus", "gain": 1.0, "pan": 0.5}
      ]
    }
  },
  "mixer_lines": {
    "drums_bus": {
      "name": "drums_bus",
      "include": ["kick", "snare"],
      "volume": 0.9,
      "pan": 0.5,
      "output": 0,
      "dynamics": {
        "compressor_threshold": 0.5,
        "compressor_ratio": 4.0
      },
      "fx": {
        "reverb_send": 0.3,
        "reverb_room": 0.8,
        "delay_send": 0.2
      }
    }
  },
  "sequences": {
    "kick": {
      "track_id": "kick",
      "events": [
        {"step": 0, "velocity": 1.0},
        {"step": 4, "velocity": 1.0}
      ]
    },
    "snare": {
      "track_id": "snare",
      "events": [
        {"step": 4, "velocity": 0.9},
        {"step": 12, "velocity": 0.9}
      ]
    }
  },
  "apply": {"timing": "bar"}
}
```

---

## Version History

### v1.0 (2026-01-31)

- Initial stable release
- `Event.offset_ms` field added for micro-timing
- Full 4-layer IR architecture
- Mixer lines with dynamics and spatial effects

### v1.1 (Planned)

- Remove `Environment.scale` (deprecated)
- Remove `Environment.chords` (deprecated)
- Simplify IR for language-agnostic use

---

**Document Version**: 1.0
**Last Updated**: 2026-02-24
**Next Review**: v1.1 release
