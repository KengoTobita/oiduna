# Oiduna

Real-time SuperDirt/MIDI loop engine with HTTP API

## Features

- 🎵 256-step fixed loop engine
- 🎹 SuperDirt (OSC) and MIDI output
- 🌐 HTTP REST API with FastAPI
- 🏗️ Clean 4-layer architecture
- 🔄 Timeline-based pattern scheduling
- 🎛️ Real-time playback control

## Installation

```bash
pip install oiduna
```

## Quick Start

```python
from oiduna import Session, create_loop_engine

# Create session
session = Session()

# Create and start engine
engine = create_loop_engine(
    osc_host="127.0.0.1",
    osc_port=57120
)
engine.start()
```

## HTTP API

```bash
# Start API server
uvicorn oiduna.application.api.main:app --host 0.0.0.0 --port 57122

# Health check
curl http://localhost:57122/health

# API documentation
open http://localhost:57122/docs
```

## Documentation

- [Architecture](ARCHITECTURE.md) - 4-layer architecture overview
- [Migration Guide](MIGRATION_GUIDE.md) - v0.x → v1.0 migration
- [API Reference](docs/API_REFERENCE.md) - HTTP API documentation

## Development

```bash
# Clone repository
git clone https://github.com/KengoTobita/oiduna.git
cd oiduna

# Install dependencies
uv sync

# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=src
```

## Architecture

Oiduna follows a clean 4-layer architecture:

### Domain Layer
Business logic and data models
- `models/` - Core data structures (Session, Track, Pattern, Event)
- `schedule/` - Schedule compilation and validation
- `session/` - Session management
- `timeline/` - Timeline and change management

### Infrastructure Layer
Technical implementations
- `execution/` - LoopEngine and runtime execution
  - Services: DriftCorrector, ConnectionMonitor, HeartbeatService, StepExecutor
- `routing/` - Message routing and scheduling
- `transport/` - OSC/MIDI senders and protocols
- `ipc/` - Inter-process communication
- `auth/` - Authentication and token management

### Application Layer
Use cases and orchestration
- `api/` - FastAPI routes and services
- `factory/` - Component factories

### Interface Layer
External interfaces
- `cli/` - Command-line interface
- `client/` - HTTP client library

## License

MIT

## Version

1.0.0 - 4-layer architecture
