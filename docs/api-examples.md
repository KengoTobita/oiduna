# Oiduna API Examples

Complete examples for all HTTP endpoints.

## Base URL

```bash
BASE_URL="http://localhost:8000"
```

## Health & Info

### Health Check

```bash
curl -X GET $BASE_URL/health
```

Response:
```json
{"status": "ok"}
```

### API Info

```bash
curl -X GET $BASE_URL/
```

Response:
```json
{
  "name": "Oiduna API",
  "version": "0.1.0",
  "description": "Real-time SuperDirt/MIDI loop engine HTTP API",
  "docs": "/docs",
  "health": "/health"
}
```

## Playback Control

### Get Playback Status

```bash
curl -X GET $BASE_URL/playback/status
```

Response:
```json
{
  "playing": false,
  "playback_state": "stopped",
  "bpm": 120,
  "position": {"step": 0, "beat": 0, "bar": 0},
  "active_tracks": [],
  "has_pending": false,
  "scenes": [],
  "current_scene": null
}
```

### Load Pattern (Compiled Session)

```bash
curl -X POST $BASE_URL/playback/pattern \
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

Response:
```json
{"status": "ok"}
```

### Start Playback

```bash
curl -X POST $BASE_URL/playback/start
```

Response:
```json
{"status": "ok"}
```

### Stop Playback

```bash
curl -X POST $BASE_URL/playback/stop
```

Response:
```json
{"status": "ok"}
```

### Pause Playback

```bash
curl -X POST $BASE_URL/playback/pause
```

Response:
```json
{"status": "ok"}
```

### Set BPM

```bash
curl -X POST $BASE_URL/playback/bpm \
  -H "Content-Type: application/json" \
  -d '{"bpm": 140}'
```

Response:
```json
{"status": "ok", "bpm": 140}
```

## Track Management

### List Tracks

```bash
curl -X GET $BASE_URL/tracks
```

Response:
```json
{
  "tracks": [
    {
      "id": "bd",
      "sound": "bd",
      "orbit": 0,
      "gain": 1.0,
      "pan": 0.5,
      "muted": false,
      "solo": false,
      "length": 4
    }
  ]
}
```

### Get Track Details

```bash
curl -X GET $BASE_URL/tracks/bd
```

Response:
```json
{
  "id": "bd",
  "sound": "bd",
  "orbit": 0,
  "gain": 1.0,
  "pan": 0.5,
  "muted": false,
  "solo": false,
  "length": 4
}
```

### Mute Track

```bash
curl -X POST $BASE_URL/tracks/bd/mute \
  -H "Content-Type: application/json" \
  -d '{"muted": true}'
```

Response:
```json
{"status": "ok"}
```

### Solo Track

```bash
curl -X POST $BASE_URL/tracks/bd/solo \
  -H "Content-Type: application/json" \
  -d '{"solo": true}'
```

Response:
```json
{"status": "ok"}
```

## Scene Management

### Activate Scene

```bash
curl -X POST $BASE_URL/scene/activate \
  -H "Content-Type: application/json" \
  -d '{"scene_id": "intro"}'
```

Response:
```json
{
  "status": "ok",
  "scene_id": "intro",
  "applied_at": {"step": 0, "beat": 0}
}
```

## MIDI Management

### List MIDI Ports

```bash
curl -X GET $BASE_URL/midi/ports
```

Response:
```json
{
  "ports": [
    {
      "name": "IAC Driver Bus 1",
      "is_input": true,
      "is_output": false
    },
    {
      "name": "IAC Driver Bus 1",
      "is_input": false,
      "is_output": true
    }
  ]
}
```

### Select MIDI Port

```bash
curl -X POST $BASE_URL/midi/port \
  -H "Content-Type: application/json" \
  -d '{"port_name": "IAC Driver Bus 1"}'
```

Response:
```json
{
  "status": "ok",
  "port_name": "IAC Driver Bus 1"
}
```

### MIDI Panic (All Notes Off)

```bash
curl -X POST $BASE_URL/midi/panic
```

Response:
```json
{"status": "ok"}
```

## Server-Sent Events (SSE)

### Stream Events

```bash
curl -X GET $BASE_URL/stream \
  -H "Accept: text/event-stream"
```

Event stream format:
```
event: connected
data: {"timestamp": 1234567890.123}

event: position
data: {"step": 0, "beat": 0, "bar": 0}

event: status
data: {"playing": true, "playback_state": "playing"}

event: heartbeat
data: {"timestamp": 1234567905.456}
```

Event types:
- `connected` - Initial connection event
- `position` - Step/beat/bar position updates
- `status` - Playback state changes
- `tracks` - Track list updates
- `error` - Engine errors
- `heartbeat` - Keep-alive (every 15 seconds)

## Error Handling

All endpoints return errors in this format:

```json
{
  "detail": "Error message here"
}
```

Common HTTP status codes:
- `200` - Success
- `422` - Validation error (invalid request data)
- `500` - Server error (engine error)

Example validation error:
```bash
curl -X POST $BASE_URL/playback/bpm \
  -H "Content-Type: application/json" \
  -d '{"bpm": -10}'
```

Response (422):
```json
{
  "detail": [
    {
      "type": "greater_than",
      "loc": ["body", "bpm"],
      "msg": "Input should be greater than 0",
      "input": -10
    }
  ]
}
```

## Environment Variables

Set these before starting the server:

```bash
# OSC Configuration
export OSC_HOST=127.0.0.1
export OSC_PORT=57120

# MIDI Configuration
export MIDI_PORT="IAC Driver Bus 1"

# API Configuration
export API_HOST=0.0.0.0
export API_PORT=8000
```

Or use a `.env` file:
```bash
OSC_HOST=127.0.0.1
OSC_PORT=57120
MIDI_PORT=IAC Driver Bus 1
API_HOST=0.0.0.0
API_PORT=8000
```

## Interactive API Documentation

Oiduna provides automatic interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
