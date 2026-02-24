# Oiduna API Reference

**Version**: 1.0
**Last Updated**: 2026-02-24
**Base URL**: `http://localhost:57122`

Complete reference for all Oiduna HTTP endpoints.

---

## Table of Contents

1. [Overview](#overview)
2. [Playback Control](#playback-control)
3. [Realtime Trigger](#realtime-trigger)
4. [Change Management](#change-management)
5. [Client Metadata](#client-metadata)
6. [Track Management](#track-management)
7. [Scene Management](#scene-management)
8. [MIDI Management](#midi-management)
9. [Asset Management](#asset-management)
10. [Server-Sent Events (SSE)](#server-sent-events-sse)
11. [Error Handling](#error-handling)

---

## Overview

### Base URL

```
http://localhost:57122
```

### Content Type

All POST/PATCH requests require:
```
Content-Type: application/json
```

### Authentication

None required (local API).

### API Documentation

- **Swagger UI**: http://localhost:57122/docs
- **ReDoc**: http://localhost:57122/redoc

---

## Playback Control

### POST /playback/session

Load a complete compiled session.

**Request**:
```json
{
  "environment": {
    "bpm": 120.0,
    "default_gate": 1.0,
    "swing": 0.0,
    "loop_steps": 256
  },
  "tracks": {
    "kick": {
      "meta": {"track_id": "kick", "mute": false, "solo": false},
      "params": {"s": "bd", "gain": 1.0, "pan": 0.5, "orbit": 0},
      "fx": {},
      "track_fx": {},
      "sends": []
    }
  },
  "tracks_midi": {},
  "mixer_lines": {},
  "sequences": {
    "kick": {
      "track_id": "kick",
      "events": [
        {"step": 0, "velocity": 1.0, "gate": 1.0},
        {"step": 4, "velocity": 1.0, "gate": 1.0}
      ]
    }
  },
  "scenes": {},
  "apply": {
    "timing": "bar",
    "track_ids": [],
    "scene_name": null
  }
}
```

**Response** (200):
```json
{
  "status": "ok",
  "message": "Session loaded successfully"
}
```

**Errors**:
- 422: Validation error (invalid IR structure)
- 500: Engine error

**Example**:
```bash
curl -X POST http://localhost:57122/playback/session \
  -H "Content-Type: application/json" \
  -d @session.json
```

---

### PATCH /playback/environment

Update global environment settings.

**Request**:
```json
{
  "bpm": 140.0,
  "swing": 0.1,
  "default_gate": 0.9
}
```

**Response** (200):
```json
{
  "status": "ok",
  "environment": {
    "bpm": 140.0,
    "swing": 0.1,
    "default_gate": 0.9,
    "loop_steps": 256
  }
}
```

**Example**:
```bash
curl -X PATCH http://localhost:57122/playback/environment \
  -H "Content-Type: application/json" \
  -d '{"bpm": 140.0}'
```

---

### PATCH /playback/tracks/{track_id}/params

Update track parameters.

**Path Parameters**:
- `track_id` (string): Track identifier

**Request**:
```json
{
  "gain": 0.8,
  "pan": 0.3,
  "cutoff": 2000.0
}
```

**Response** (200):
```json
{
  "status": "ok",
  "track_id": "kick",
  "updated_params": {
    "gain": 0.8,
    "pan": 0.3,
    "cutoff": 2000.0
  }
}
```

**Example**:
```bash
curl -X PATCH http://localhost:57122/playback/tracks/kick/params \
  -H "Content-Type: application/json" \
  -d '{"gain": 0.8}'
```

---

### POST /playback/start

Start playback.

**Request**: None

**Response** (200):
```json
{
  "status": "ok",
  "playing": true
}
```

**Example**:
```bash
curl -X POST http://localhost:57122/playback/start
```

---

### POST /playback/stop

Stop playback.

**Request**: None

**Response** (200):
```json
{
  "status": "ok",
  "playing": false
}
```

**Example**:
```bash
curl -X POST http://localhost:57122/playback/stop
```

---

### POST /playback/pause

Pause playback (resume with /playback/start).

**Request**: None

**Response** (200):
```json
{
  "status": "ok",
  "playing": false,
  "paused": true
}
```

**Example**:
```bash
curl -X POST http://localhost:57122/playback/pause
```

---

### GET /playback/status

Get current playback status.

**Response** (200):
```json
{
  "playing": true,
  "playback_state": "playing",
  "bpm": 120.0,
  "position": {
    "step": 64,
    "beat": 16,
    "bar": 4
  },
  "active_tracks": ["kick", "snare", "hihat"],
  "has_pending": false,
  "scenes": ["intro", "verse", "chorus"],
  "current_scene": "verse"
}
```

**Fields**:
- `playing` (bool): Is engine currently running
- `playback_state` (string): "stopped" | "playing" | "paused"
- `bpm` (float): Current tempo
- `position.step` (int): Current step (0-255)
- `position.beat` (int): Current beat (0-based)
- `position.bar` (int): Current bar (0-based)
- `active_tracks` (array): List of track IDs
- `has_pending` (bool): Are there pending changes
- `scenes` (array): Available scene names
- `current_scene` (string | null): Active scene name

**Example**:
```bash
curl http://localhost:57122/playback/status
```

---

## Realtime Trigger

### POST /playback/trigger/osc

Trigger SuperDirt sound immediately (bypass sequencer).

**Request**:
```json
{
  "track_id": "kick",
  "velocity": 0.8,
  "note": null
}
```

**Response** (200):
```json
{
  "status": "ok",
  "message": "OSC trigger sent"
}
```

**Use Case**: Live MIDI controller input, manual triggering

**Example**:
```bash
curl -X POST http://localhost:57122/playback/trigger/osc \
  -H "Content-Type: application/json" \
  -d '{"track_id": "kick", "velocity": 1.0}'
```

---

### POST /playback/trigger/midi

Trigger MIDI note immediately.

**Request**:
```json
{
  "track_id": "midi_synth",
  "note": 60,
  "velocity": 100,
  "duration_ms": 500
}
```

**Response** (200):
```json
{
  "status": "ok",
  "message": "MIDI trigger sent"
}
```

**Example**:
```bash
curl -X POST http://localhost:57122/playback/trigger/midi \
  -H "Content-Type: application/json" \
  -d '{"track_id": "midi_synth", "note": 60, "velocity": 100}'
```

---

## Change Management

### DELETE /playback/changes/{change_id}

Cancel a pending change.

**Path Parameters**:
- `change_id` (string): Change identifier

**Response** (200):
```json
{
  "status": "ok",
  "cancelled_id": "change_123"
}
```

**Example**:
```bash
curl -X DELETE http://localhost:57122/playback/changes/change_123
```

---

### GET /playback/changes/pending

List all pending changes.

**Response** (200):
```json
{
  "pending": [
    {
      "id": "change_123",
      "type": "track_update",
      "track_id": "kick",
      "apply_timing": "bar",
      "apply_at_step": 0
    }
  ]
}
```

**Example**:
```bash
curl http://localhost:57122/playback/changes/pending
```

---

### POST /playback/changes/cancel-all

Cancel all pending changes.

**Request**: None

**Response** (200):
```json
{
  "status": "ok",
  "cancelled_count": 3
}
```

**Example**:
```bash
curl -X POST http://localhost:57122/playback/changes/cancel-all
```

---

## Client Metadata

### POST /session/clients/{client_id}/metadata

Register or update client metadata.

**Path Parameters**:
- `client_id` (string): Client identifier (e.g., "user_alice_mars")

**Request**:
```json
{
  "scale": "C_major",
  "key": "C",
  "chords": ["Cmaj7", "Dm7", "G7", "Cmaj7"],
  "chord_position": 0,
  "bpm_suggestion": 120,
  "message": "Starting with II-V-I in C",
  "distribution_type": "mars",
  "client_name": "Alice"
}
```

**Response** (200):
```json
{
  "client_id": "user_alice_mars",
  "updated_at": 1234567890.123
}
```

**Notes**:
- Metadata structure is flexible (any JSON object)
- Oiduna stores but does not interpret metadata
- Other clients can query this metadata via GET endpoints
- SSE broadcasts `client_metadata_updated` events

**Example**:
```bash
curl -X POST http://localhost:57122/session/clients/user_alice_mars/metadata \
  -H "Content-Type: application/json" \
  -d '{"scale": "C_major", "chord_position": 0}'
```

---

### GET /session/clients

Get all clients and their metadata.

**Response** (200):
```json
{
  "user_alice_mars": {
    "metadata": {
      "scale": "C_major",
      "chord_position": 2,
      "message": "Moving to G7"
    },
    "updated_at": 1234567890.123
  },
  "dj_bob_tidal": {
    "metadata": {
      "scale": "C_major",
      "following": "user_alice_mars"
    },
    "updated_at": 1234567891.456
  }
}
```

**Example**:
```bash
curl http://localhost:57122/session/clients
```

---

### GET /session/clients/{client_id}

Get specific client metadata.

**Path Parameters**:
- `client_id` (string): Client identifier

**Response** (200):
```json
{
  "metadata": {
    "scale": "C_major",
    "chord_position": 2
  },
  "updated_at": 1234567890.123
}
```

**Error** (404):
```json
{
  "detail": "Client not found"
}
```

**Example**:
```bash
curl http://localhost:57122/session/clients/user_alice_mars
```

---

### DELETE /session/clients/{client_id}

Remove client from session (call on disconnect).

**Path Parameters**:
- `client_id` (string): Client identifier

**Response** (200):
```json
{
  "status": "ok",
  "removed_client_id": "user_alice_mars"
}
```

**Example**:
```bash
curl -X DELETE http://localhost:57122/session/clients/user_alice_mars
```

---

## Track Management

### GET /tracks

List all tracks.

**Response** (200):
```json
{
  "tracks": [
    {
      "id": "kick",
      "sound": "bd",
      "orbit": 0,
      "gain": 1.0,
      "pan": 0.5,
      "muted": false,
      "solo": false,
      "length": 16
    }
  ]
}
```

**Example**:
```bash
curl http://localhost:57122/tracks
```

---

### GET /tracks/{track_id}

Get track details.

**Path Parameters**:
- `track_id` (string): Track identifier

**Response** (200):
```json
{
  "id": "kick",
  "sound": "bd",
  "orbit": 0,
  "gain": 1.0,
  "pan": 0.5,
  "muted": false,
  "solo": false,
  "length": 16
}
```

**Example**:
```bash
curl http://localhost:57122/tracks/kick
```

---

### POST /tracks/{track_id}/mute

Mute or unmute a track.

**Path Parameters**:
- `track_id` (string): Track identifier

**Request**:
```json
{
  "muted": true
}
```

**Response** (200):
```json
{
  "status": "ok",
  "track_id": "kick",
  "muted": true
}
```

**Example**:
```bash
curl -X POST http://localhost:57122/tracks/kick/mute \
  -H "Content-Type: application/json" \
  -d '{"muted": true}'
```

---

### POST /tracks/{track_id}/solo

Solo or unsolo a track.

**Path Parameters**:
- `track_id` (string): Track identifier

**Request**:
```json
{
  "solo": true
}
```

**Response** (200):
```json
{
  "status": "ok",
  "track_id": "kick",
  "solo": true
}
```

**Example**:
```bash
curl -X POST http://localhost:57122/tracks/kick/solo \
  -H "Content-Type: application/json" \
  -d '{"solo": true}'
```

---

## Scene Management

### POST /scene/activate

Activate a scene.

**Request**:
```json
{
  "scene_id": "verse",
  "timing": "bar"
}
```

**Response** (200):
```json
{
  "status": "ok",
  "scene_id": "verse",
  "applied_at": {
    "step": 0,
    "beat": 0
  }
}
```

**Example**:
```bash
curl -X POST http://localhost:57122/scene/activate \
  -H "Content-Type: application/json" \
  -d '{"scene_id": "verse"}'
```

---

## MIDI Management

### GET /midi/ports

List available MIDI ports.

**Response** (200):
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

**Example**:
```bash
curl http://localhost:57122/midi/ports
```

---

### POST /midi/port

Select MIDI output port.

**Request**:
```json
{
  "port_name": "IAC Driver Bus 1"
}
```

**Response** (200):
```json
{
  "status": "ok",
  "port_name": "IAC Driver Bus 1"
}
```

**Error** (404):
```json
{
  "detail": "MIDI port not found"
}
```

**Example**:
```bash
curl -X POST http://localhost:57122/midi/port \
  -H "Content-Type: application/json" \
  -d '{"port_name": "IAC Driver Bus 1"}'
```

---

### POST /midi/panic

Send MIDI panic (all notes off on all channels).

**Request**: None

**Response** (200):
```json
{
  "status": "ok",
  "message": "MIDI panic sent (all notes off)"
}
```

**Example**:
```bash
curl -X POST http://localhost:57122/midi/panic
```

---

## Asset Management

### POST /assets/samples

Upload custom audio sample.

**Request** (multipart/form-data):
- `file` (file): Audio file (.wav, .aif, .flac)
- `category` (string): Sample category (e.g., "kicks", "snares")

**Response** (200):
```json
{
  "status": "ok",
  "filename": "my_kick.wav",
  "category": "kicks",
  "path": "/samples/kicks/my_kick.wav"
}
```

**Example**:
```bash
curl -X POST http://localhost:57122/assets/samples \
  -F "file=@my_kick.wav" \
  -F "category=kicks"
```

---

### GET /assets/samples

List uploaded samples.

**Response** (200):
```json
{
  "samples": {
    "kicks": ["my_kick.wav", "808_kick.wav"],
    "snares": ["my_snare.wav"]
  }
}
```

**Example**:
```bash
curl http://localhost:57122/assets/samples
```

---

### POST /assets/synthdefs

Upload SuperCollider SynthDef.

**Request** (multipart/form-data):
- `file` (file): SynthDef file (.scsyndef)
- `name` (string): SynthDef name

**Response** (200):
```json
{
  "status": "ok",
  "name": "mysynth",
  "path": "/synthdefs/mysynth.scsyndef"
}
```

**Example**:
```bash
curl -X POST http://localhost:57122/assets/synthdefs \
  -F "file=@mysynth.scsyndef" \
  -F "name=mysynth"
```

---

## Server-Sent Events (SSE)

### GET /stream

Real-time event stream.

**Headers**:
```
Accept: text/event-stream
```

**Event Types**:

#### connected
Initial connection confirmation.
```
event: connected
data: {"timestamp": 1234567890.123}
```

#### position
Step/beat/bar position updates (sent every step).
```
event: position
data: {"step": 64, "beat": 16, "bar": 4}
```

#### status
Playback state changes.
```
event: status
data: {"playing": true, "playback_state": "playing"}
```

#### tracks
Track list updates.
```
event: tracks
data: {"active_tracks": ["kick", "snare", "hihat"]}
```

#### client_metadata_updated
Client metadata changed.
```
event: client_metadata_updated
data: {
  "client_id": "user_alice_mars",
  "metadata": {"chord_position": 2},
  "updated_at": 1234567890.123
}
```

#### client_connected
New client registered.
```
event: client_connected
data: {"client_id": "dj_bob_tidal"}
```

#### client_disconnected
Client removed.
```
event: client_disconnected
data: {"client_id": "user_alice_mars"}
```

#### error
Engine error occurred.
```
event: error
data: {"message": "OSC send failed", "details": "..."}
```

#### heartbeat
Keep-alive ping (every 15 seconds).
```
event: heartbeat
data: {"timestamp": 1234567905.456}
```

**Example**:
```bash
curl -N http://localhost:57122/stream
```

**JavaScript Example**:
```javascript
const eventSource = new EventSource('http://localhost:57122/stream');

eventSource.addEventListener('position', (e) => {
  const pos = JSON.parse(e.data);
  console.log(`Step: ${pos.step}, Beat: ${pos.beat}, Bar: ${pos.bar}`);
});

eventSource.addEventListener('client_metadata_updated', (e) => {
  const update = JSON.parse(e.data);
  console.log(`Client ${update.client_id} updated:`, update.metadata);
});
```

---

## Error Handling

### Error Response Format

```json
{
  "detail": "Error message here"
}
```

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request |
| 404 | Not Found |
| 422 | Validation Error |
| 500 | Server Error |

### Validation Error (422)

**Example Request**:
```bash
curl -X PATCH http://localhost:57122/playback/environment \
  -H "Content-Type: application/json" \
  -d '{"bpm": -10}'
```

**Response** (422):
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

### Server Error (500)

**Example Response**:
```json
{
  "detail": "Loop engine error: OSC connection refused"
}
```

---

## Timing Control

All session update endpoints support timing control via `apply` parameter:

**Request**:
```json
{
  "data": { ... },
  "timing": {
    "type": "boundary",
    "unit": "bar"
  }
}
```

**Timing Types**:

### Boundary Timing
Apply at next beat/bar/sequence boundary.

```json
{
  "type": "boundary",
  "unit": "beat" | "bar" | "seq"
}
```

| Unit | Applies at |
|------|-----------|
| `"beat"` | Next beat (step % 4 == 0) |
| `"bar"` | Next bar (step % 16 == 0) |
| `"seq"` | Sequence start (step == 0) |

### Absolute Timing
Apply at specific step.

```json
{
  "type": "absolute",
  "step": 128
}
```

| Field | Range | Description |
|-------|-------|-------------|
| `step` | 0-255 | Exact step to apply at |

**Default**: `{"type": "boundary", "unit": "bar"}`

**Example**:
```bash
curl -X POST http://localhost:57122/playback/session \
  -H "Content-Type: application/json" \
  -d '{
    "data": { ... },
    "timing": {"type": "boundary", "unit": "bar"}
  }'
```

---

## Environment Variables

Configure via environment or `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `OSC_HOST` | 127.0.0.1 | SuperDirt OSC host |
| `OSC_PORT` | 57120 | SuperDirt OSC port |
| `API_HOST` | 0.0.0.0 | API server bind address |
| `API_PORT` | 57122 | API server port |
| `MIDI_PORT` | - | Default MIDI port name |

**Example `.env`**:
```bash
OSC_HOST=127.0.0.1
OSC_PORT=57120
API_HOST=0.0.0.0
API_PORT=57122
MIDI_PORT=IAC Driver Bus 1
```

---

## Rate Limiting

None currently implemented. Future consideration for production deployments.

---

## CORS

Enabled for all origins in development. Configure for production deployments.

---

**Document Version**: 1.0
**Last Updated**: 2026-02-24
**API Version**: 1.0
