# Changelog

All notable changes to oiduna will be documented in this file.

## [Unreleased]

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
