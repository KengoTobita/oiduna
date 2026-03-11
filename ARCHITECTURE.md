# Oiduna Architecture (v1.0)

## Overview

Oiduna v1.0 uses a **4-layer architecture** pattern that clearly separates concerns and makes dependencies explicit.

```
┌─────────────────────────────────────────────────────┐
│  Layer 4: Interface                                  │
│  CLI, HTTP Client                                    │
│  (oiduna.interface)                                  │
└─────────────────────┬───────────────────────────────┘
                      │ depends on
┌─────────────────────▼───────────────────────────────┐
│  Layer 3: Application                                │
│  FastAPI Routes, Services, Factories                 │
│  (oiduna.application)                                │
└─────────────────────┬───────────────────────────────┘
                      │ depends on
┌─────────────────────▼───────────────────────────────┐
│  Layer 2: Infrastructure                             │
│  LoopEngine, Routing, Transport, IPC, Auth           │
│  (oiduna.infrastructure)                             │
└─────────────────────┬───────────────────────────────┘
                      │ depends on
┌─────────────────────▼───────────────────────────────┐
│  Layer 1: Domain                                     │
│  Models, Schedule, Timeline, Session                 │
│  (oiduna.domain)                                     │
└─────────────────────────────────────────────────────┘
```

## Layer 1: Domain (`oiduna.domain`)

**Purpose:** Business logic and domain models. No dependencies on infrastructure or frameworks.

### `oiduna.domain.models`
Core data models using Pydantic.

**Key Classes:**
- `Session` - Top-level container for all state
- `Track` - Musical tracks with destination and parameters
- `Pattern` - Event sequences within tracks
- `PatternEvent` - Individual scheduled musical events
- `ClientInfo` - Client authentication and metadata
- `Environment` - Global session settings (BPM, metadata)

**Timing Types:**
- `StepNumber`, `BeatNumber`, `CycleFloat`
- `BPM`, `Milliseconds`

**Example:**
```python
from oiduna.domain.models import Session, Track, Pattern

session = Session()
track = Track(track_id="drums", destination_id="superdirt")
pattern = Pattern(pattern_id="kick")
```

### `oiduna.domain.schedule`
Schedule compilation and message validation.

**Key Classes:**
- `ScheduleEntry` - Single scheduled message (frozen dataclass)
- `LoopSchedule` - 256-step loop schedule (immutable)
- `SessionCompiler` - Converts Session → LoopSchedule
- `OscValidator`, `MidiValidator` - Protocol validators

**Design Principle:** Immutable, dataclass-based (not Pydantic) for performance.

**Example:**
```python
from oiduna.domain.schedule import SessionCompiler

batch = SessionCompiler.compile(session)
print(f"Compiled {len(batch.entries)} messages")
```

### `oiduna.domain.timeline`
Cued change timeline for multi-loop-ahead scheduling.

**Key Classes:**
- `CuedChange` - Single scheduled change (frozen dataclass)
- `CuedChangeTimeline` - Manages future pattern changes

**Example:**
```python
from oiduna.domain.timeline import CuedChangeTimeline, CuedChange

timeline = CuedChangeTimeline()
change = CuedChange(
    target_global_step=1024,
    batch=compiled_batch,
    client_id="alice_001"
)
timeline.add_change(change)
```

### `oiduna.domain.session`
Session management and business logic validation.

**Key Classes:**
- `SessionContainer` - Lightweight manager container
- `SessionValidator` - Business logic validation
- Managers: `ClientManager`, `TrackManager`, `PatternManager`, etc.

**Example:**
```python
from oiduna.domain.session import SessionContainer

container = SessionContainer()
container.client_manager.create_client("alice")
```

## Layer 2: Infrastructure (`oiduna.infrastructure`)

**Purpose:** Technical implementations and external interfaces.

### `oiduna.infrastructure.execution`
Real-time loop execution engine.

**Key Classes:**
- `LoopEngine` - 256-step fixed loop engine
- `RuntimeState` - Playback state management
- `ClockGenerator` - MIDI clock generation (24 PPQ)
- `CommandHandler` - Playback command handling

**Critical File:** `loop_engine.py` (1,032 lines) - Main execution engine

**Design Principles:**
- 256 steps fixed (never changes)
- <1ms latency requirement
- Thread-safe state management

**Example:**
```python
from oiduna.infrastructure.execution import LoopEngine

engine = LoopEngine(osc=osc_sender, midi=midi_sender)
engine.start()
engine.set_schedule(compiled_batch)
```

### `oiduna.infrastructure.routing`
Message routing and destination management.

**Key Classes:**
- `DestinationRouter` - Routes messages to OSC/MIDI destinations
- `LoopScheduler` - Runtime message scheduling

**Example:**
```python
from oiduna.infrastructure.routing import DestinationRouter

router = DestinationRouter()
router.add_destination("superdirt", osc_config)
```

### `oiduna.infrastructure.transport`
OSC and MIDI output adapters.

**Key Classes:**
- `OscSender` - OSC message transmission
- `MidiSender` - MIDI message transmission
- `OscDestinationSender`, `MidiDestinationSender` - Higher-level senders

**Protocols:** `MidiOutput`, `OscOutput`

**Example:**
```python
from oiduna.infrastructure.transport import OscSender, MidiSender

osc = OscSender(host="127.0.0.1", port=57120, address="/dirt/play")
midi = MidiSender(port_name="IAC Driver Bus 1")
```

### `oiduna.infrastructure.ipc`
Inter-process communication.

**Key Classes:**
- `InProcessStateProducer` - In-process state publishing
- `NoopCommandConsumer` - No-op command consumer
- Protocols: `CommandConsumer`, `StateProducer`

### `oiduna.infrastructure.auth`
Authentication and token management.

**Key Functions:**
- `verify_admin_password()` - Admin password verification
- `TokenManager` - Client token management

**Example:**
```python
from oiduna.infrastructure.auth import verify_admin_password

verify_admin_password("secret123")
```

## Layer 3: Application (`oiduna.application`)

**Purpose:** Use cases and application services.

### `oiduna.application.factory`
Factory functions for creating infrastructure components.

**Key Functions:**
- `create_loop_engine()` - Creates production LoopEngine with DI

**Example:**
```python
from oiduna.application.factory import create_loop_engine

engine = create_loop_engine(
    osc_host="127.0.0.1",
    osc_port=57120,
    midi_port="IAC Driver Bus 1"
)
```

### `oiduna.application.api`
FastAPI application with routes and services.

**Structure:**
- `main.py` - FastAPI app entry point
- `routes/` - API route handlers (playback, session, tracks, patterns, etc.)
- `services/` - Business logic services
- `dependencies.py` - FastAPI dependency injection

**Example:**
```python
from oiduna.application.api.main import app

# Run with uvicorn:
# uvicorn oiduna.application.api.main:app --reload
```

## Layer 4: Interface (`oiduna.interface`)

**Purpose:** CLI and HTTP clients.

### `oiduna.interface.cli`
Command-line interface for Oiduna.

**Commands:**
- `play` - Play patterns
- `status` - Check engine status
- `sample` - Manage samples
- `synthdef` - Manage SynthDefs

### `oiduna.interface.client`
HTTP client library for API access.

**Key Classes:**
- `OidunaClient` - HTTP client wrapper
- Pattern/Track/Session helpers

## Dependency Rules

### Allowed Dependencies

```
Interface    → Application, Infrastructure, Domain  ✅
Application  → Infrastructure, Domain                ✅
Infrastructure → Domain                              ✅
Domain       → (none - self-contained)               ✅
```

### Forbidden Dependencies

```
Domain       → Infrastructure  ❌
Domain       → Application     ❌
Infrastructure → Application   ❌
```

## Top-Level API (`oiduna`)

For convenience, the most commonly used classes are exposed at the top level:

```python
from oiduna import (
    # Version
    __version__,

    # Domain models
    Session, Track, Pattern, PatternEvent,
    ClientInfo, Environment,
    StepNumber, BeatNumber, CycleFloat,

    # Domain schedule
    ScheduleEntry, LoopSchedule, SessionCompiler,

    # Domain timeline
    CuedChange, CuedChangeTimeline,

    # Domain session
    SessionContainer, SessionValidator,

    # Infrastructure
    LoopEngine, DestinationRouter, LoopScheduler,
    OscSender, MidiSender,

    # Application
    create_loop_engine, app,
)
```

## Design Principles

### 1. Immutability Where It Matters

**Domain schedule uses frozen dataclasses:**
```python
@dataclass(frozen=True, slots=True)
class ScheduleEntry:
    destination_id: str
    cycle: float
    step: int
    params: dict[str, Any]
```

**Why:** Thread-safe, cacheable, minimal memory footprint.

### 2. Pydantic for Domain Models

**Domain models use Pydantic:**
```python
class Session(BaseModel):
    tracks: dict[str, Track] = Field(default_factory=dict)
    environment: Environment = Field(default_factory=Environment)
```

**Why:** Runtime validation, JSON serialization, IDE support.

### 3. Protocol-Based Interfaces

**Infrastructure uses Protocols:**
```python
class OscOutput(Protocol):
    def send(self, params: dict[str, Any]) -> None: ...
```

**Why:** Loose coupling, easy testing, dependency inversion.

### 4. No Framework Dependencies in Domain

Domain layer has zero dependencies on FastAPI, uvicorn, or any framework.

**Why:** Domain logic is portable, testable, and framework-independent.

## Testing Strategy

### Unit Tests by Layer

```
tests/
├── domain/            # Pure business logic tests
├── infrastructure/    # Infrastructure component tests
├── application/       # API route and service tests
└── integration/       # End-to-end integration tests
```

### Test Principles

1. **Domain tests** - No mocks, pure logic
2. **Infrastructure tests** - Mock external I/O
3. **Application tests** - Use FastAPI test client
4. **Integration tests** - Full system tests

## Performance Characteristics

### Loop Engine
- **Latency:** <1ms per step
- **Fixed loop:** 256 steps (never changes)
- **BPM range:** 20-999 BPM
- **MIDI clock:** 24 PPQ (pulses per quarter note)

### Memory Usage
- **ScheduleEntry:** Minimal (frozen dataclass with slots)
- **Session:** Pydantic overhead (~5-10% compared to pure dict)
- **Timeline:** O(n) where n = number of pending changes

## Future Architecture Considerations

### Potential Extensions

1. **Plugin System** - Extension points in execution layer
2. **Multiple Engines** - Support for parallel loop engines
3. **Distributed Mode** - IPC for multi-process execution
4. **Web UI** - Additional interface layer

### Architectural Constraints

- **256-step loop is fixed** - Changing this would require major refactor
- **Single-threaded execution** - Loop engine runs in one thread
- **In-process by default** - IPC is opt-in

## Version

This architecture applies to:
- **Oiduna v1.0.0** (4-layer architecture)

---

*Last updated: March 2026*
