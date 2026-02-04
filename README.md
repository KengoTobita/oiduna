# Oiduna

Real-time SuperDirt/MIDI loop engine with HTTP API.

## Features

- HTTP REST API for remote control
- SSE (Server-Sent Events) for real-time state
- OSC output to SuperDirt
- MIDI device support
- Docker deployment

## Quick Start

### 方法1: 自動起動設定（推奨）

```bash
# 一度だけセットアップ
./scripts/setup_superdirt.sh

# 以降は簡単起動
sclang                           # SuperDirt自動起動
uv run python -m oiduna_api.main # Oiduna API起動
```

### 方法2: スクリプト起動

```bash
./scripts/start_superdirt.sh     # SuperDirt起動
uv run python -m oiduna_api.main # Oiduna API起動
```

### 方法3: 統合起動（tmux）

```bash
./scripts/start_all.sh  # SuperDirt + Oiduna APIを一発起動
```

詳細: [Quick Start Guide](docs/quick-start.md)

### Docker

```bash
docker build -t oiduna .
docker run -p 8000:8000 --network host oiduna
```

## API Documentation

- **[API Examples](docs/api-examples.md)** - Complete curl examples for all endpoints
- **[Data Model](docs/data-model.md)** - Data structure reference
- **[Interactive Docs](http://localhost:8000/docs)** - Swagger UI (when server is running)

### Main Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/playback/pattern` | POST | Load compiled session pattern |
| `/playback/start` | POST | Start playback |
| `/playback/stop` | POST | Stop playback |
| `/playback/pause` | POST | Pause playback |
| `/playback/bpm` | POST | Change BPM |
| `/playback/status` | GET | Get current playback status |
| `/tracks` | GET | List all tracks |
| `/tracks/{id}` | GET | Get track details |
| `/tracks/{id}/mute` | POST | Mute/unmute track |
| `/tracks/{id}/solo` | POST | Solo/unsolo track |
| `/scene/activate` | POST | Activate scene |
| `/midi/ports` | GET | List MIDI ports |
| `/midi/port` | POST | Select MIDI port |
| `/midi/panic` | POST | MIDI panic (all notes off) |
| `/stream` | GET (SSE) | Real-time state stream |
| `/assets/samples` | POST | Upload custom samples |
| `/assets/samples` | GET | List uploaded samples |
| `/assets/synthdefs` | POST | Upload SynthDefs |

### Example: Load a Pattern

```bash
curl -X POST http://localhost:8000/playback/pattern \
  -H "Content-Type: application/json" \
  -d '{
    "environment": {"bpm": 120},
    "tracks": {
      "bd": {
        "sound": "bd",
        "orbit": 0,
        "gain": 1.0,
        "pan": 0.5,
        "mute": false,
        "solo": false,
        "sequence": [
          {"pitch": "0", "start": 0, "length": 1}
        ]
      }
    },
    "sequences": {}
  }'
```

### Example: Start Playback

```bash
curl -X POST http://localhost:8000/playback/start
```

### Example: Stream State

```bash
curl http://localhost:8000/stream
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OSC_HOST` | 127.0.0.1 | SuperDirt OSC host |
| `OSC_PORT` | 57120 | SuperDirt OSC port |
| `API_HOST` | 0.0.0.0 | API server host |
| `API_PORT` | 8000 | API server port |
| `MIDI_PORT` | - | MIDI output port name |

## Architecture

Oiduna consists of two main packages:

- **oiduna_loop** - Core loop engine with SuperDirt/MIDI support
- **oiduna_api** - FastAPI HTTP server wrapping the engine

The API uses Pydantic for request/response validation and provides automatic OpenAPI documentation at `/docs` and `/redoc`.

## License

MIT
