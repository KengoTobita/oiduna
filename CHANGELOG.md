# Changelog

All notable changes to oiduna will be documented in this file.

## [Unreleased]

### Code Quality Improvements (2026-02-27)

**Bug Fixes**:
- Fixed LoopEngine calling non-existent RuntimeState methods (`should_apply_pending()`, `apply_pending_changes()`, `get_effective()`)
- Fixed incorrect method call `get_active_tracks()` → `get_active_track_ids()`
- Removed broken symlinks in test directory

**Type Safety**:
- Fixed all relative imports to use absolute imports (oiduna_scheduler.*, oiduna_destination.*)
- Removed sys.path manipulation hack in loop_engine.py
- Standardized type hints to Python 3.13 syntax (list[], dict[], | for unions)
- Added proper generic type parameters for hook signatures

**Architecture Cleanup**:
- **REMOVED**: `POST /api/patterns` endpoint (violates responsibility boundary)
  - Pattern management is now exclusively client responsibility
  - Clients should send ScheduledMessageBatch to `POST /playback/session` instead
- **CHANGED**: LoopEngine command handlers are now public API
  - `_handle_play()` → `handle_play()` (can be called directly from routes)
  - `_handle_stop()` → `handle_stop()`
  - `_handle_pause()` → `handle_pause()`

**Refactoring** (Martin Fowler patterns applied):
- **Extract Class**: Created `CommandHandler` class for command processing
  - Extracted playback command logic from LoopEngine (play, stop, pause, mute, solo, bpm, panic)
  - LoopEngine reduced from 1,034 lines → ~850 lines (18% reduction)
  - Clear separation of concerns: CommandHandler handles state changes, LoopEngine handles engine-specific logic (MIDI, drift correction)
- **Extract Method**: Simplified `_step_loop()` method
  - Cyclomatic complexity reduced from 12+ to <5
  - New helper methods: `_execute_current_step()`, `_get_filtered_messages()`, `_apply_hooks()`, `_send_messages()`, `_wait_for_next_step()`, `_publish_periodic_updates()`
  - Each method now <20 lines with clear single responsibility

**Code Cleanup**:
- Removed commented-out code blocks
- **All 328 tests passing** ✅

### BREAKING CHANGE - Architecture Unification (2026-02-26)

**Complete transition to ScheduledMessageBatch architecture** - CompiledSession and related infrastructure have been completely removed. Oiduna now exclusively uses ScheduledMessageBatch for all pattern data.

**What Changed**:

1. **Removed CompiledSession Infrastructure**
   - Deleted all IR models: `CompiledSession`, `Track`, `EventSequence`, `Environment`, `Scene`, `MixerLine`, etc.
   - Deleted `SessionToMessagesConverter` (converters/ directory removed)
   - Deleted all CompiledSession-related tests

2. **Simplified RuntimeState** (624 lines → ~280 lines)
   - Removed: CompiledSession management, deep merge logic, Scene/Apply functionality
   - Kept: Playback state, BPM management, mute/solo filtering
   - **New**: Track-based mute/solo filtering using `track_id` from params
   - **New**: `filter_messages()` method for filtering ScheduledMessage lists
   - **New**: `register_track()` for tracking known track_ids

3. **Removed API Endpoints**
   - `POST /playback/pattern` - CompiledSession endpoint removed
   - `POST /scene/activate` - Scene endpoints removed
   - `GET /scenes` - Scene endpoints removed

4. **Simplified LoopEngine**
   - Deleted `_handle_compile()`, `_handle_scene()`, `_handle_scenes()` methods
   - Removed `compile()` and `activate_scene()` public API methods
   - **Only `POST /playback/session` endpoint remains** for loading patterns
   - Added mute/solo filtering in `_step_loop()` before sending messages

**Migration Guide**:

**Old API (CompiledSession - REMOVED)**:
```python
# This no longer works
compiled_session = {
    "environment": {"bpm": 120, ...},
    "tracks": {"kick": {...}, ...},
    "sequences": {"kick": {...}, ...},
    "scenes": {...},
    "apply": {"timing": "bar", "track_ids": ["kick"]}
}
POST /playback/pattern
```

**New API (ScheduledMessageBatch - ONLY option)**:
```python
# Use this instead
message_batch = {
    "messages": [
        {
            "destination_id": "superdirt",
            "cycle": 0.0,
            "step": 0,
            "params": {
                "track_id": "kick",  # REQUIRED for mute/solo
                "s": "bd",
                "gain": 0.8,
                "pan": 0.5
            }
        },
        # ...
    ],
    "bpm": 120.0,
    "pattern_length": 4.0
}
POST /playback/session
```

**Important**:
- `track_id` in `params` is **required** for mute/solo filtering to work
- Messages without `track_id` will always be sent (not filtered)
- MARS/Distribution must now generate ScheduledMessageBatch format
- Scene expansion and apply timing are now **client-side responsibility**

**Mute/Solo Changes**:
- Mute/Solo endpoints still exist: `POST /tracks/{id}/mute`, `POST /tracks/{id}/solo`
- Filtering now happens at message send time based on `params["track_id"]`
- Solo takes priority: if any tracks are soloed, only those play
- Unknown track_ids are inactive by default

**Status Response Changes**:
```python
# Old fields (removed)
"has_pending", "scenes", "current_scene"

# New fields
"known_tracks", "muted_tracks", "soloed_tracks"
```

**Why This Change**:
- Dramatic code simplification: removed 20+ files, 500+ lines
- Clear responsibility boundaries: Distribution = pattern generation, Oiduna = scheduling + routing
- Better performance: no deep merging, no session caching
- Unified architecture: one data format throughout

**Impact**:
- **MARS_for_oiduna compiler must be updated** to output ScheduledMessageBatch
- All existing compiled sessions are incompatible
- Tests using CompiledSession fixtures must be rewritten

---

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
