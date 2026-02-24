# Oiduna Architecture

**Version**: 1.0
**Last Updated**: 2026-02-24
**Status**: Stable

---

## Table of Contents

1. [Design Philosophy](#design-philosophy)
2. [System Architecture](#system-architecture)
3. [Layered IR Design](#layered-ir-design)
4. [Data Flow](#data-flow)
5. [Loop Engine Details](#loop-engine-details)
6. [Architectural Decision Records](#architectural-decision-records)

---

## Design Philosophy

### Oiduna's Mission

Oiduna exists to eliminate the phrase "we can't do that technically" from live coding:

```
1. "We can't do that technically" → Never
2. "Standard approaches should be surprisingly easy" → Always
3. "Non-standard approaches are possible with Distribution-side adjustments" → Flexible
```

### Core Principles

#### 1. Simplicity Over Features

Oiduna Core is intentionally minimal:

- **256-step fixed loop** - No variable loop lengths, no complex time signatures
- **No DSL parsing** - Receives pre-compiled IR only
- **No music theory** - Works with concrete MIDI note numbers, not scales/chords
- **No audio generation** - Delegates to SuperDirt and MIDI devices

**Why**: A simple, stable core enables complex creativity at higher layers.

#### 2. Separation of Concerns

```
┌─────────────────────────────────────────────────────┐
│                  Oiduna Core                        │
│  - 256 step fixed format player                    │
│  - No music theory concepts                        │
│  - Receives pre-resolved note numbers              │
│  - Simple, stable, fast                            │
└─────────────────────────────────────────────────────┘
                      ▲
                      │ IR (JSON)
                      │ (concrete note numbers)
                      │
┌─────────────────────┴───────────────────────────────┐
│              Distribution (Multiple possible)       │
│  - DSL parsing & compilation                       │
│  - Pitch resolution (scale/chord → note numbers)   │
│  - Time signature & music theory processing        │
│  - Conversion to Oiduna format                     │
│  - Creative freedom & custom implementation        │
└─────────────────────────────────────────────────────┘
```

**Oiduna's Responsibility**: Playback engine, timing precision, output routing
**Distribution's Responsibility**: Music theory, DSL design, pitch resolution

This separation enables:
- Multiple DSLs (MARS, TidalCycles-like, custom) to target Oiduna
- Oiduna improvements benefit all Distributions
- Distribution innovation doesn't require Oiduna changes

#### 3. Immutability & Type Safety

All IR models are:
- **Immutable** (`dataclass(frozen=True)`) - Predictable, thread-safe, cacheable
- **Type-safe** (Python 3.13 + mypy) - Compile-time error detection
- **Self-documenting** - Types serve as live documentation

#### 4. Performance by Design

- **O(1) event lookup** - Step index for constant-time event retrieval
- **Fixed loop length** - Eliminates boundary condition complexity
- **Anchor-based timing** - Prevents drift accumulation
- **Minimal allocations** - Immutable data structures enable sharing

---

## System Architecture

### Package Structure

```
oiduna/
├── packages/
│   ├── oiduna_core/          # Core engine & models
│   │   ├── ir/               # IR data models (4 layers)
│   │   ├── engine/           # Loop engine implementation
│   │   ├── output/           # OSC/MIDI senders
│   │   └── modulation/       # Parameter modulation
│   │
│   └── oiduna_api/           # HTTP API server
│       ├── routes/           # FastAPI routes
│       ├── models/           # API request/response models
│       └── main.py           # API entry point
│
├── scripts/                  # Startup scripts
├── docs/                     # Documentation
└── tests/                    # Test suites
```

### Dependency Map

```
┌─────────────────────────────────────────┐
│           oiduna_api                    │
│  - FastAPI HTTP server                  │
│  - Pydantic validation                  │
│  - SSE streaming                        │
│  - OpenAPI docs                         │
└──────────────┬──────────────────────────┘
               │ depends on
               ↓
┌─────────────────────────────────────────┐
│           oiduna_core                   │
│  - IR models (immutable dataclasses)    │
│  - Loop engine (5 concurrent tasks)     │
│  - OSC sender (python-osc)              │
│  - MIDI sender (python-rtmidi)          │
└──────────────┬──────────────────────────┘
               │ outputs to
        ┌──────┴───────┐
        ↓              ↓
┌─────────────┐  ┌─────────────┐
│ SuperDirt   │  │ MIDI Device │
│ (OSC/UDP)   │  │             │
└─────────────┘  └─────────────┘
```

### External Dependencies

**Core (`oiduna_core`)**:
- `python-osc` - OSC protocol for SuperDirt
- `python-rtmidi` - MIDI output
- `mido` - MIDI message handling

**API (`oiduna_api`)**:
- `fastapi` - HTTP server framework
- `uvicorn` - ASGI server
- `pydantic` - Data validation
- `sse-starlette` - Server-Sent Events

**Notable Absences**:
- ❌ No `pyzmq` - Uses HTTP instead of ZeroMQ (vs original MARS)
- ❌ No `lark` - No DSL parsing in core
- ❌ No audio libraries - Delegates to SuperCollider

---

## Layered IR Design

Oiduna uses a **4-layer IR (Intermediate Representation)** architecture. Each layer has a distinct purpose and can be modified independently.

### Overview

```
CompiledSession
│
├── 🌍 Environment Layer
│   Purpose: Global playback settings
│   Models:  Environment, Chord
│
├── 🎛️ Configuration Layer
│   Purpose: Individual track/mixer settings
│   Models:  Track, TrackMidi, MixerLine
│
├── 🎵 Pattern Layer
│   Purpose: Time-axis event definitions
│   Models:  EventSequence, Event
│
└── 🎮 Control Layer
    Purpose: Playback control & snapshots
    Models:  Scene, ApplyCommand
```

### Why Layered?

**Traditional Approach** (monolithic):
```python
# Everything mixed together
track = {
    "bpm": 120,              # Environment concern
    "sound": "bd",           # Configuration concern
    "events": [...],         # Pattern concern
    "apply_at": "bar"        # Control concern
}
# Hard to modify one aspect without affecting others
```

**Oiduna Approach** (layered):
```python
session = CompiledSession(
    environment=Environment(bpm=120),           # Layer 1
    tracks={"bd": Track(...)},                  # Layer 2
    sequences={"bd": EventSequence(...)},       # Layer 3
    apply=ApplyCommand(timing="bar")            # Layer 4
)
# Each layer can be modified independently
```

### Layer 1: Environment

**Responsibility**: Settings shared across all tracks

**Models**: `Environment`, `Chord`

**Key Fields**:
```python
@dataclass(frozen=True)
class Environment:
    bpm: float = 120.0              # Tempo
    default_gate: float = 1.0       # Default note length
    swing: float = 0.0              # Swing amount (0.0-1.0)
    loop_steps: int = 256           # Fixed, immutable
```

**Design Notes**:
- `loop_steps` is always 256, never changes
- BPM changes affect all tracks simultaneously
- Future: `scale` and `chords` fields will be removed (v1.1) - music theory belongs in Distribution

**Why Separate**: Ensures all tracks play at the same tempo, prevents inconsistencies.

### Layer 2: Configuration

**Responsibility**: Per-track audio settings and routing

**Three Track Types**:

#### Audio Tracks (SuperDirt)

**Model**: `Track`

```python
@dataclass(frozen=True)
class Track:
    meta: TrackMeta              # ID, mute, solo
    params: TrackParams          # Sound parameters
    fx: FxParams                 # Legacy effects
    track_fx: TrackFxParams      # Tone shaping (v5)
    sends: tuple[Send, ...]      # Mixer routing
    modulations: dict[str, Modulation]
```

**Signal Flow**:
```
Event → Track.params (s, gain, pan) → Track.track_fx (filter, dist)
     → Send → MixerLine → MixerLine.fx (reverb, delay) → Output
```

#### MIDI Tracks

**Model**: `TrackMidi`

```python
@dataclass(frozen=True)
class TrackMidi:
    track_id: str
    channel: int                 # MIDI channel (0-15)
    velocity: int = 127
    transpose: int = 0           # Semitones
    mute: bool = False
    solo: bool = False
    cc_modulations: dict[int, Modulation]
```

#### Mixer Lines

**Model**: `MixerLine`

```python
@dataclass(frozen=True)
class MixerLine:
    name: str                    # e.g., "drums_bus"
    include: tuple[str, ...]     # Track IDs in this line
    volume: float = 1.0
    pan: float = 0.5
    mute: bool = False
    solo: bool = False
    output: int = 0              # Output orbit
    dynamics: MixerLineDynamics  # Limiter, compressor
    fx: MixerLineFx              # Reverb, delay, leslie
```

**Why Three Types**: Different responsibilities (audio synthesis, MIDI control, bus mixing) require different fields. Extensible for future types (CV, OSC).

### Layer 3: Pattern

**Responsibility**: Defining *when* and *what* to play

**Models**: `EventSequence`, `Event`

```python
@dataclass(frozen=True, slots=True)
class Event:
    step: int                    # Position (0-255)
    velocity: float = 1.0        # Intensity (0.0-1.0)
    note: int | None = None      # MIDI note number
    gate: float = 1.0            # Note length ratio
    offset_ms: float = 0.0       # Micro-timing (NEW in v1.0)

@dataclass(frozen=True)
class EventSequence:
    track_id: str
    _events: tuple[Event, ...]
    _step_index: dict[int, list[int]]  # O(1) lookup
```

**Step Index Design**:
```python
# Construction (once)
_step_index = {
    0: [0, 1, 2],    # Events at step 0
    4: [3],          # Event at step 4
    8: [4, 5],       # Events at step 8
    # ... sparse dictionary
}

# Lookup (every tick, must be O(1))
current_step = 64
event_indices = sequence._step_index.get(current_step, [])  # O(1)
for idx in event_indices:
    event = sequence._events[idx]
    send_to_superdirt(event)
```

**Why Separate from Configuration**: Same pattern can be played with different sounds. Pattern changes don't affect track settings.

### Layer 4: Control

**Responsibility**: *When* and *how* to apply changes

**Models**: `Scene`, `ApplyCommand`

#### Scenes

**Model**: `Scene`

```python
@dataclass(frozen=True)
class Scene:
    name: str
    environment: Environment | None      # Override global settings
    tracks: dict[str, Track]             # Track snapshots
    tracks_midi: dict[str, TrackMidi]
    sequences: dict[str, EventSequence]
    mixer_lines: dict[str, MixerLine]
```

**Use Case**: Switch between "intro", "verse", "chorus" configurations on-the-fly.

#### Apply Commands

**Model**: `ApplyCommand`

```python
@dataclass(frozen=True)
class ApplyCommand:
    timing: Literal["now", "beat", "bar", "seq"]  # When to apply
    track_ids: list[str]                          # Which tracks (empty = all)
    scene_name: str | None                        # Optional scene reference
```

**Why Separate**: Pattern data (what to play) is independent from control metadata (when to apply). Enables queuing, synchronization, and real-time updates.

---

## Data Flow

### Complete Flow: Client → Audio Output

```
┌──────────────────────────────────────────┐
│ 1. Client (e.g., MARS Distribution)     │
│    - Write DSL code                      │
│    - Compile to CompiledSession          │
│    - Serialize to JSON                   │
└───────────────┬──────────────────────────┘
                │
                │ HTTP POST /playback/session
                │ Content-Type: application/json
                ↓
┌──────────────────────────────────────────┐
│ 2. Oiduna API (FastAPI)                  │
│    - Parse JSON                          │
│    - Validate with Pydantic              │
│    - Deserialize to CompiledSession      │
└───────────────┬──────────────────────────┘
                │
                │ Python object
                ↓
┌──────────────────────────────────────────┐
│ 3. Loop Engine (oiduna_core)             │
│    ┌─ Environment: Apply BPM             │
│    ├─ Configuration: Initialize tracks   │
│    ├─ Pattern: Build step indices        │
│    └─ Control: Schedule application      │
└───────────────┬──────────────────────────┘
                │
                │ Start 256-step loop
                ↓
┌──────────────────────────────────────────┐
│ 4. Loop Execution (every ~31ms @ 120BPM) │
│    For each step:                        │
│      1. Check step_index for events      │  O(1) lookup
│      2. Merge Event + Track params       │
│      3. Generate OSC/MIDI messages       │
│      4. Send to outputs                  │
└───────────────┬──────────────────────────┘
                │
         ┌──────┴───────┐
         ↓              ↓
┌────────────────┐  ┌──────────────┐
│ 5a. SuperDirt  │  │ 5b. MIDI Out │
│  (OSC/UDP)     │  │  (rtmidi)    │
│  /dirt/play    │  │  Note On/Off │
└────────┬───────┘  └──────┬───────┘
         ↓                 ↓
    🔊 Audio Output   🎹 MIDI Synth
```

### Sequence Diagram

```
Client          API             Engine          SuperDirt
  │              │               │               │
  ├─POST session─>│               │               │
  │              ├─deserialize───>│               │
  │              │               ├─build indices─>│
  │              │<──ok──────────┤               │
  │<─201─────────┤               │               │
  │              │               │               │
  ├─POST start──>│               │               │
  │              ├─start()──────>│               │
  │              │               ├─loop begins───┤
  │<─200─────────┤               │               │
  │              │               │               │
  │              │               ├─step 0────────>│
  │              │               ├─step 1────────>│
  │              │               ├─step 2────────>│
  │              │               │  (continues)  │
```

### Timing Diagram

```
Time (ms)   Step    Action
─────────────────────────────────────────────
0           0       ┌─ Load session
                    │  - Deserialize IR
                    │  - Build step indices  (~10ms)
                    └─ Ready

10          0       ┌─ Start command
                    └─ Begin loop

10          0       ┌─ Tick 0
                    │  - Lookup events (O(1))
                    │  - Send OSC messages
                    └─ Wait for next step

41          1       ┌─ Tick 1
                    └─ ...

72          2       ┌─ Tick 2
                    └─ ...

(31ms per step @ 120 BPM, 256 steps)
```

---

## Loop Engine Details

### Architecture

The Loop Engine runs **5 concurrent asyncio tasks**:

```python
async def run_engine():
    async with asyncio.TaskGroup() as tg:
        tg.create_task(step_loop())        # Main sequencer
        tg.create_task(clock_loop())       # MIDI clock (24 PPQ)
        tg.create_task(note_off_loop())    # MIDI note-off scheduler
        tg.create_task(command_loop())     # Real-time commands
        tg.create_task(heartbeat_loop())   # Connection monitoring
```

### Task Responsibilities

#### 1. Step Loop (Main Sequencer)

**Frequency**: ~31ms per step (@ 120 BPM)
**Responsibility**: Process events at each step

```python
async def step_loop():
    while playing:
        current_step = position.step  # 0-255

        # O(1) event lookup
        for seq in sequences.values():
            event_indices = seq._step_index.get(current_step, [])
            for idx in event_indices:
                event = seq._events[idx]
                process_event(event)

        # Advance step
        position.step = (position.step + 1) % 256

        # Wait for next step (anchor-based timing)
        await sleep_until(next_step_time)
```

**Timing Strategy**: Anchor-based to prevent drift
```python
# BAD: Accumulates drift
await asyncio.sleep(step_duration)  # Each sleep has ~1-2ms error

# GOOD: Anchored to start time
loop_start = time.perf_counter()
step_count = 0
while True:
    target_time = loop_start + (step_count * step_duration)
    await sleep_until(target_time)  # Corrects drift each step
    step_count += 1
```

#### 2. Clock Loop (MIDI Sync)

**Frequency**: ~5.2ms per tick (24 PPQ @ 120 BPM)
**Responsibility**: Send MIDI clock messages

```python
async def clock_loop():
    while playing:
        midi_sender.send_clock()
        await asyncio.sleep(clock_interval)  # 24 ticks per beat
```

#### 3. Note-Off Loop

**Frequency**: Variable (based on scheduled note-offs)
**Responsibility**: Send MIDI note-off messages

```python
async def note_off_loop():
    while True:
        now = time.perf_counter()
        due_notes = [n for n in scheduled_notes if n.off_time <= now]
        for note in due_notes:
            midi_sender.send_note_off(note.channel, note.pitch)
        await asyncio.sleep(0.001)  # 1ms resolution
```

#### 4. Command Loop

**Frequency**: Variable (event-driven)
**Responsibility**: Process real-time commands

```python
async def command_loop():
    while True:
        cmd = await command_queue.get()
        match cmd:
            case "load_session": load_session(cmd.data)
            case "start": start_playback()
            case "stop": stop_playback()
```

#### 5. Heartbeat Loop

**Frequency**: 5 seconds
**Responsibility**: Monitor connections, emit SSE heartbeats

```python
async def heartbeat_loop():
    while True:
        check_connections()
        emit_sse_heartbeat()
        await asyncio.sleep(5.0)
```

### Concurrency Model

```
┌──────────────────────────────────────────┐
│        Python asyncio Event Loop         │
│  (Single-threaded, cooperative)          │
│                                          │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐ │
│  │ Step    │  │ Clock   │  │ Note    │ │
│  │ Loop    │  │ Loop    │  │ Off     │ │
│  └─────────┘  └─────────┘  └─────────┘ │
│  ┌─────────┐  ┌─────────┐              │
│  │ Command │  │ Heart   │              │
│  │ Loop    │  │ beat    │              │
│  └─────────┘  └─────────┘              │
└──────────────────────────────────────────┘
         │
         │ GIL (Global Interpreter Lock)
         │ Shared across all tasks
         ↓
    Performance consideration:
    - Heavy processing blocks all tasks
    - See PERFORMANCE.md for mitigation
```

---

## Architectural Decision Records

### ADR-001: Why HTTP API?

**Context**: Original MARS used ZeroMQ for IPC.

**Decision**: Use HTTP REST API for Oiduna.

**Rationale**:
1. **Language Agnostic** - Any language can be a Distribution (Python, Rust, JavaScript)
2. **No Binary Dependencies** - No `pyzmq` compilation issues
3. **Debugging** - curl, browsers, standard tools work out-of-the-box
4. **Firewall Friendly** - Works over networks, through proxies
5. **Self-Documenting** - OpenAPI/Swagger automatic docs

**Trade-offs**:
- ❌ Slightly higher latency (~1-2ms vs ZeroMQ ~0.1ms)
- ✅ Acceptable for ~31ms step resolution
- ❌ More overhead than binary protocols
- ✅ JSON is human-readable and debuggable

**Status**: Stable

### ADR-002: Why 256 Fixed Steps?

**Context**: Could support variable loop lengths (128, 256, 512, etc.).

**Decision**: Fixed 256 steps, immutable.

**Rationale**:
1. **Simplicity** - No edge cases for loop boundaries
2. **O(1) Indexing** - Fixed-size arrays, predictable memory
3. **Hardware Inspiration** - Classic sequencers (TR-808, Octatrack) use fixed lengths
4. **Distribution Flexibility** - Distributions can map any time signature to 256 steps

**Trade-offs**:
- ❌ Unusual time signatures require Distribution-side mapping
- ✅ But this is Distribution's responsibility anyway
- ❌ Can't have 1024-step mega-loops
- ✅ But 256 steps = 32 seconds @ 120 BPM (sufficient for most use cases)

**Examples**:
```
4/4: 16 bars × 16 steps/bar = 256 steps (perfect fit)
3/4: 21 bars × 12 steps/bar = 252 steps (4 unused)
5/4: 12 bars × 20 steps/bar = 240 steps (16 unused)
7/8: 18 bars × 14 steps/bar = 252 steps (4 unused)
```

**Status**: Stable

### ADR-003: Why Step Index?

**Context**: Could iterate all events every step, or use binary search.

**Decision**: Pre-compute step→events index.

**Rationale**:
1. **O(1) Lookup** - Constant time, critical for real-time
2. **Memory Trade-off** - Extra dict, but small (~1KB for typical session)
3. **Build Once** - Computed at load time, not per-tick

**Performance**:
```
Naive search:    O(N) per step, N = total events (unacceptable)
Binary search:   O(log N) per step (acceptable, but not optimal)
Step index:      O(1) per step (optimal)

Real-world @ 120 BPM, 50 tracks, 256 steps:
- Naive: 12,800 comparisons/tick = ~400μs (misses 31ms budget)
- Index: 50 dict lookups = ~5μs (comfortable)
```

**Status**: Stable

### ADR-004: Why Immutable IR?

**Context**: Could use mutable dataclasses or plain dicts.

**Decision**: All IR models use `dataclass(frozen=True)`.

**Rationale**:
1. **Predictability** - Data never changes after creation
2. **Thread Safety** - No locking needed, safe concurrent access
3. **Cacheability** - Hashable, can be dict keys
4. **Debugging** - Easier to reason about, no hidden mutations

**Trade-offs**:
- ❌ Updates require creating new objects
- ✅ But session updates are infrequent (~once per pattern change)
- ❌ Slightly more memory (can't reuse objects)
- ✅ But modern GC handles this well

**Status**: Stable

### ADR-005: Why 4 Layers, Not 3?

**Context**: Original design called it "3-layer IR".

**Decision**: Rename to "4-layer" or "Layered IR".

**Rationale**:
1. **Clarity** - Configuration layer has 3 distinct types (Track, TrackMidi, MixerLine)
2. **Control Layer** - ApplyCommand is separate from Pattern data
3. **Extensibility** - Easy to add new layer types (e.g., Automation Layer in future)

**Layers**:
1. Environment - Global settings
2. Configuration - Track/mixer setup
3. Pattern - Time-axis events
4. Control - Application timing

**Status**: Adopted in documentation

### ADR-006: Why Separate API Package?

**Context**: Could have single monolithic package.

**Decision**: Split `oiduna_core` and `oiduna_api`.

**Rationale**:
1. **Reusability** - Core can be embedded without HTTP dependencies
2. **Testing** - Core logic testable without FastAPI
3. **Alternative Interfaces** - Could add gRPC, WebSocket, CLI using same core
4. **Dependency Isolation** - Web concerns don't leak into engine

**Trade-offs**:
- ❌ More files, more packages
- ✅ Clearer boundaries, better architecture

**Status**: Stable

---

## Future Directions

### Considered for v1.1+

1. **Multi-Process Loop Engine** - Isolate engine from API for GIL independence (see PERFORMANCE.md)
2. **Remove Music Theory Fields** - Delete `Environment.scale` and `Environment.chords` (Distribution responsibility)
3. **Control Voltage (CV) Tracks** - Add `TrackCV` for modular synth control
4. **Automation Layer** - 5th IR layer for parameter automation
5. **Binary Protocol** - Protobuf or MessagePack alternative to JSON for low-latency

### Not Planned

1. **Variable Loop Lengths** - Conflicts with simplicity principle
2. **Built-in DSL** - Oiduna is a player, not a compiler
3. **Audio Synthesis** - SuperCollider does this better
4. **DAW Features** - Out of scope (project management, recording, etc.)

---

## Conclusion

Oiduna's architecture prioritizes:
1. **Simplicity** - Fixed format, minimal concepts
2. **Separation** - Clear boundaries between engine and Distributions
3. **Performance** - O(1) lookups, immutable data, anchor-based timing
4. **Flexibility** - Layered IR enables independent modifications

This design enables **both standard and experimental use cases** while maintaining a **simple, stable core**.

---

**Document Version**: 1.0
**Last Updated**: 2026-02-24
**Next Review**: v1.1 release
