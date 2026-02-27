# Oiduna

**Real-time SuperDirt/MIDI loop engine with HTTP API**

Oiduna is a 256-step loop sequencer that receives pre-compiled patterns via HTTP and outputs to SuperDirt (OSC) and MIDI devices. It serves as the playback engine for live coding environments like MARS DSL.

---

## Key Features

- 🎵 **256-step fixed loop** - Simple, predictable timing
- 🌐 **HTTP REST API** - Language-agnostic, curl-friendly
- 🔊 **SuperDirt integration** - OSC output to SuperCollider
- 🎹 **MIDI output** - Hardware synth support
- 📡 **Server-Sent Events (SSE)** - Real-time state streaming
- 🎛️ **Effects support** - Via SuperDirt and extension plugins
- 🔄 **O(1) event lookup** - Optimized for real-time performance

---

## Quick Start

### Prerequisites

- **Python 3.13+** with **uv** package manager
- **SuperCollider** with **SuperDirt** (for audio output)

### Installation

```bash
# Install Oiduna core
cd /path/to/oiduna
uv sync

# Install SuperDirt extension (for audio output)
cd ../oiduna-extension-superdirt
uv pip install -e .
```

### SuperDirt Setup

For SuperDirt audio output, see the extension's documentation:

**[→ SuperDirt Extension Setup Guide](../oiduna-extension-superdirt/README.md)**

The extension provides:
- Automated SuperCollider configuration scripts
- SuperDirt startup scripts
- Orbit management
- Parameter conversion (snake_case → camelCase)

### Launch Oiduna

```bash
# Terminal 1: Start Oiduna API
cd oiduna
uv run python -m oiduna_api.main

# Terminal 2: Start SuperDirt (if using audio output)
# See oiduna-extension-superdirt/README.md for setup
```

### Verify Installation

```bash
# Health check
curl http://localhost:57122/health
# → {"status": "ok"}

# Load a simple pattern
curl -X POST http://localhost:57122/playback/session \
  -H "Content-Type: application/json" \
  -d '{
    "environment": {"bpm": 120},
    "tracks": {
      "kick": {
        "meta": {"track_id": "kick", "mute": false, "solo": false},
        "params": {"s": "bd", "gain": 1.0, "pan": 0.5, "orbit": 0},
        "fx": {}, "track_fx": {}, "sends": []
      }
    },
    "tracks_midi": {},
    "mixer_lines": {},
    "sequences": {
      "kick": {
        "track_id": "kick",
        "events": [
          {"step": 0, "velocity": 1.0},
          {"step": 4, "velocity": 1.0},
          {"step": 8, "velocity": 1.0},
          {"step": 12, "velocity": 1.0}
        ]
      }
    },
    "scenes": {},
    "apply": null
  }'

# Start playback
curl -X POST http://localhost:57122/playback/start

# 🔊 You should hear a kick drum!

# Stop playback
curl -X POST http://localhost:57122/playback/stop
```

---

## Documentation

### Getting Started

- **[OIDUNA_CONCEPTS.md](docs/OIDUNA_CONCEPTS.md)** - What is Oiduna? Core concepts and terminology
- **[TERMINOLOGY.md](docs/TERMINOLOGY.md)** - Glossary of terms

### Architecture & Design

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System design, 3-layer IR, data flow, ADRs
- **[DATA_MODEL_REFERENCE.md](docs/DATA_MODEL_REFERENCE.md)** - Complete IR model specification
- **[PERFORMANCE.md](docs/PERFORMANCE.md)** - Performance characteristics and optimization

### API & Usage

- **[API_REFERENCE.md](docs/API_REFERENCE.md)** - All 22 HTTP endpoints with examples
- **[USAGE_PATTERNS.md](docs/USAGE_PATTERNS.md)** - Common use cases and patterns
- **[Interactive Docs](http://localhost:57122/docs)** - Swagger UI (when server running)

### Development

- **DEVELOPMENT_GUIDE.md** - Setup, testing, contribution guide (準備中)
- **[DISTRIBUTION_GUIDE.md](docs/DISTRIBUTION_GUIDE.md)** - Building custom Distributions (DSLs)


---

## Architecture Overview

```
┌─────────────────────────────────────────┐
│ Distribution (e.g., MARS DSL)           │
│  - DSL parsing                          │
│  - Music theory (scales, chords)       │
│  - Compile to IR                        │
└──────────────┬──────────────────────────┘
               │ HTTP POST (JSON)
               ↓
┌─────────────────────────────────────────┐
│ Oiduna Core                             │
│  - 256-step loop engine                 │
│  - OSC/MIDI output                      │
│  - No music theory (just note numbers)  │
└──────────────┬──────────────────────────┘
               │
        ┌──────┴──────┐
        ↓             ↓
  SuperDirt        MIDI Device
  (audio)          (hardware)
```

### 3-Layer IR Model

Oiduna uses a layered Intermediate Representation:

1. **🌍 Environment Layer** - Global settings (BPM, swing)
2. **🎛️ Configuration Layer** - Tracks, MIDI, mixer routing
3. **🎵 Pattern Layer** - Time-based events (when to play what)
4. **🎮 Control Layer** - Scenes, timing control

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for details.

---

## Main API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/playback/session` | POST | Load compiled session |
| `/playback/start` | POST | Start playback |
| `/playback/stop` | POST | Stop playback |
| `/playback/status` | GET | Get current status |
| `/playback/environment` | PATCH | Update BPM, swing, etc. |
| `/playback/tracks/{id}/params` | PATCH | Update track parameters |
| `/playback/trigger/osc` | POST | Manual OSC trigger |
| `/playback/trigger/midi` | POST | Manual MIDI trigger |
| `/session/clients/{id}/metadata` | POST | Share client metadata |
| `/session/clients` | GET | Get all client metadata |
| `/tracks` | GET | List all tracks |
| `/tracks/{id}/mute` | POST | Mute/unmute track |
| `/scene/activate` | POST | Switch scene |
| `/midi/ports` | GET | List MIDI ports |
| `/stream` | GET (SSE) | Real-time event stream |

See [API_REFERENCE.md](docs/API_REFERENCE.md) for complete documentation.

---

## Environment Variables

Configure via `.env` file or environment:

```bash
OSC_HOST=127.0.0.1       # SuperDirt OSC host
OSC_PORT=57120           # SuperDirt OSC port
API_HOST=0.0.0.0         # API server bind address
API_PORT=57122           # API server port
MIDI_PORT=               # MIDI output port name (optional)
```

---

## Docker Deployment

```bash
# Build
docker build -t oiduna .

# Run
docker run -p 57122:57122 --network host oiduna
```

---

## Project Structure

```
oiduna/
├── packages/
│   ├── oiduna_core/          # Core engine & IR models
│   │   ├── ir/               # 4-layer data models
│   │   ├── engine/           # Loop engine (5 tasks)
│   │   ├── output/           # OSC/MIDI senders
│   │   └── modulation/       # Parameter automation
│   │
│   └── oiduna_api/           # HTTP API server
│       ├── routes/           # FastAPI endpoints
│       └── main.py           # Entry point
│
├── docs/                     # Documentation
├── scripts/                  # Startup scripts
└── tests/                    # Test suites
```

---

## Development

### Run with Auto-reload

```bash
uv run python -m oiduna_api.main
# Uvicorn watches for code changes and reloads automatically
```

### Run Tests

```bash
uv run pytest
```

### Type Checking

```bash
uv run mypy packages/
```

---

## Troubleshooting

### SuperDirt won't start

```supercollider
// In SuperCollider
Quarks.update;
Quarks.install("SuperDirt");
0.exit;
```

### OSC port already in use

```bash
lsof -i :57120  # Check what's using port 57120
kill <PID>      # Kill the process if needed
```

### API won't start

```bash
uv sync         # Reinstall dependencies
lsof -i :57122  # Check if port 57122 is in use
```

---

## Use Cases

- **Live Coding** - MARS DSL, TidalCycles-like languages
- **Algorithmic Composition** - Python scripts generating patterns
- **MIDI Sequencing** - Control hardware synthesizers
- **Interactive Installations** - HTTP API from any language
- **Collaborative Performance** - Client metadata sharing for B2B sessions
- **Network-based Setup** - Wi-Fi AP mode for wireless Distribution clients (see [oiduna-hotspot](https://github.com/KengoTobita/oiduna-hotspot) extension)

---

## Design Philosophy

> "We can't do that technically" → Never
> "Standard approaches should be surprisingly easy" → Always
> "Non-standard approaches possible with Distribution adjustments" → Flexible

Oiduna is intentionally minimal:
- Fixed 256-step loop (no variable lengths)
- No DSL parsing (receives compiled IR only)
- No music theory (works with MIDI note numbers)
- No audio generation (delegates to SuperDirt)

This simplicity enables **complex creativity at higher layers** (Distributions).

---

## Related Projects

- **MARS DSL** - Primary Distribution for Oiduna
- **SuperDirt** - Audio engine (SuperCollider Quark)
- **TidalCycles** - Inspiration for live coding patterns

---

## License

MIT

---

## Contributing

Development guide (準備中) will cover:
- Development environment setup
- Code contribution guidelines
- Testing procedures
- Documentation standards

---

## Version

**Oiduna Core**: v1.0
**API Version**: v1.0
**Last Updated**: 2026-02-26

---

## Links

- **Documentation**: [/docs](docs/)
- **API Docs (Swagger)**: http://localhost:57122/docs
- **API Docs (ReDoc)**: http://localhost:57122/redoc
- **GitHub Issues**: (Add your repo URL here)

---

**Oiduna** - Simple, stable, fast. Built for live coding.
