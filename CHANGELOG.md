# Changelog

All notable changes to oiduna will be documented in this file.

## [Unreleased]

### Changed - Architecture Refinement (2026-02-26)

**Dual Architecture with Clear Responsibility Boundaries** - Refined Oiduna's architecture to clarify the separation between CompiledSession (state management) and ScheduledMessageBatch (sound output).

**Oiduna's 4 Core Responsibilities** (明確化 - Clarification):
1. **①Loop Data Management** - Environment/Track/Sequence/Scenes hierarchy (MARS compatibility)
2. **②Routing** - Track→Destination mapping, client→destination routing
3. **③Protocol Validation** - OSC/MIDI specification compliance checking
4. **④Stable Operation** - Bundle sending, GC, drift correction (future enhancement)

**Implementation**:

- **Protocol Validators** (`packages/oiduna_scheduler/validators/`)
  - `OscValidator`: Validates OSC 1.0 compliance (type tags, address patterns, value ranges)
  - `MidiValidator`: Validates MIDI 1.0 compliance (note/velocity/CC ranges, channel validation)
  - Integrated into `DestinationRouter.send_messages()` for pre-send validation
  - Invalid messages logged and skipped (non-blocking)
  - 67 comprehensive tests covering edge cases and boundary conditions

- **Routing Data** (`packages/oiduna_core/ir/`)
  - Added `destination_id: str = "superdirt"` field to `Track` dataclass
  - Added `destination_id: str = "superdirt"` field to `MixerLine` dataclass
  - Default value maintains backward compatibility with existing tests
  - Serialization/deserialization support in `to_dict()`/`from_dict()`

- **Conversion Layer** (`packages/oiduna_loop/converters/`)
  - `SessionToMessagesConverter`: CompiledSession → ScheduledMessageBatch
  - Extracts BPM and pattern_length from Environment
  - Converts Events to ScheduledMessages with cycle calculation
  - Merges Track params, TrackFx, and legacy Fx into message params
  - Handles event velocity (applied to gain), note, and gate (→ sustain)
  - Legacy FX naming conversion (delay_send → delaySend for SuperDirt)
  - 13 tests covering empty sessions, multi-track, routing, param merging

- **LoopEngine Integration** (`packages/oiduna_loop/engine/loop_engine.py`)
  - `_handle_compile()` now converts CompiledSession to ScheduledMessageBatch
  - Conversion happens when destinations are loaded
  - Messages loaded into `_message_scheduler` for sound output
  - CompiledSession continues to provide state management (mute/solo, scene management)
  - Both architectures work together with clearly defined roles

**Design Rationale**:
- **Kept both architectures** instead of deleting CompiledSession
- CompiledSession: Type-safe API, MARS compatibility, state management, 79+ existing tests
- ScheduledMessageBatch: Sound output execution, content-agnostic routing
- Conversion layer bridges the two architectures cleanly

**Backward Compatibility**:
- All 376+ existing tests pass without modification
- Default `destination_id="superdirt"` maintains compatibility
- API endpoints unchanged
- No breaking changes to data formats

**Test Coverage**:
- Added 80+ new tests (67 validators + 13 converter)
- All existing tests continue to pass
- Total: 376 passed, 11 skipped

**Distribution ↔ Oiduna Boundary** (責任分担 - Role Division):
- Distribution: Generates OSC/MIDI parameter content
- Oiduna: Validates protocol compliance, routes messages, manages loop structure
- Oiduna is content-agnostic - doesn't interpret params semantics

**Future Enhancements** (Deferred):
- Stability Manager (bundle sending, GC scheduling, drift correction)
- Code cleanup (removal of genuinely unused code with user approval)

---

### Added - Extension System (2026-02-25)

**API Layer Extension System with minimal runtime hooks** - Complete plugin architecture implementation.

- **Core Extension System** (`packages/oiduna_api/extensions/`)
  - `BaseExtension` ABC with `transform()` and optional `before_send_messages()`
  - `ExtensionPipeline` for auto-discovery via entry_points
  - Dependency Injection integration with FastAPI
  - Extensions can provide custom HTTP endpoints via `get_router()`

- **Runtime Hook Integration** (`packages/oiduna_loop/`)
  - Minimal `before_send_hooks` for message finalization before sending
  - Performance target: p99 < 100μs

- **SuperDirt Reference Extension** (separate package: `oiduna-extension-superdirt`)
  - Orbit assignment (mixer_line_id → orbit)
  - Parameter name conversion (snake_case → camelCase)
  - CPS injection (BPM → cps, handles BPM changes dynamically)
  - Custom endpoints: `/superdirt/orbits`, `/superdirt/reset-orbits`

- **Documentation**
  - ADR 0006 updated with implementation details
  - Extension Development Guide (`docs/EXTENSION_DEVELOPMENT_GUIDE.md`)
  - Performance benchmarks and guidelines

**Design**: Oiduna core stays destination-agnostic; extensions add specific logic externally.

---

## [0.1.0] - 2025-02-03

### Added
- Initial release of oiduna as pure backend for real-time SuperDirt/MIDI loop handling
- HTTP REST API for remote control
- SSE (Server-Sent Events) for real-time state streaming
- OSC output to SuperDirt
- MIDI device support
- Docker deployment support
- OpenAPI 3.1 specification for client generation
- FastAPI-based HTTP server with CORS support

### API Endpoints
- `GET /health` - Health check
- `POST /compile` - Load compiled DSL session
- `POST /transport/play` - Start playback
- `POST /transport/stop` - Stop playback
- `POST /transport/pause` - Pause/resume playback
- `POST /transport/bpm` - Change BPM
- `GET /tracks` - List all tracks
- `POST /tracks/{id}/mute` - Mute/unmute track
- `POST /tracks/{id}/solo` - Solo/unsolo track
- `POST /scene/activate` - Activate scene
- `GET /midi/ports` - List MIDI ports
- `POST /midi/port` - Select MIDI port
- `POST /midi/panic` - MIDI panic (all notes off)
- `GET /state` - Real-time state stream (SSE)
