# Changelog

All notable changes to oiduna will be documented in this file.

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
