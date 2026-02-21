# Oiduna Data Model

This document describes the core data structures used in Oiduna.

## CompiledSession

The `CompiledSession` is the primary data structure for loading patterns into Oiduna. It represents a complete musical session with tracks, sequences, and environment settings.

### Schema

```typescript
interface CompiledSession {
  environment: Environment;
  tracks: Record<string, Track>;
  sequences: Record<string, Sequence>;
}
```

### Environment

Global settings for the session.

```typescript
interface Environment {
  bpm: number;              // Beats per minute (e.g., 120)
  scale?: string;           // Musical scale (e.g., "minor", "major")
  root?: string;            // Root note (e.g., "C", "D")
  [key: string]: any;       // Additional custom parameters
}
```

### Track

A single instrument track with its parameters and sequence.

```typescript
interface Track {
  sound: string;            // Sound/sample name (e.g., "bd", "sd", "hh")
  orbit: number;            // SuperDirt orbit number (0-11)
  gain: number;             // Volume (0.0-1.0)
  pan: number;              // Stereo pan (0.0=left, 0.5=center, 1.0=right)
  mute: boolean;            // Track muted state
  solo: boolean;            // Track solo state
  sequence: Event[];        // Array of events to play
  [key: string]: any;       // Additional SuperDirt parameters (e.g., cutoff, delay)
}
```

### Event

A single musical event within a sequence.

```typescript
interface Event {
  pitch: string;            // MIDI note or pitch (e.g., "60", "C4")
  start: number;            // Start time in steps (0-based)
  length: number;           // Duration in steps
  velocity?: number;        // MIDI velocity (0-127)
  [key: string]: any;       // Additional event parameters
}
```

### Sequence

A reusable sequence that can be referenced by tracks.

```typescript
interface Sequence {
  events: Event[];          // Array of events
  length?: number;          // Total length in steps
}
```

## Complete Example

```json
{
  "environment": {
    "bpm": 120,
    "scale": "minor",
    "root": "C"
  },
  "tracks": {
    "bd": {
      "sound": "bd",
      "orbit": 0,
      "gain": 1.0,
      "pan": 0.5,
      "mute": false,
      "solo": false,
      "sequence": [
        {"pitch": "0", "start": 0, "length": 1},
        {"pitch": "0", "start": 4, "length": 1},
        {"pitch": "0", "start": 8, "length": 1},
        {"pitch": "0", "start": 12, "length": 1}
      ]
    },
    "sd": {
      "sound": "sd",
      "orbit": 1,
      "gain": 0.8,
      "pan": 0.5,
      "mute": false,
      "solo": false,
      "sequence": [
        {"pitch": "0", "start": 4, "length": 1, "velocity": 100},
        {"pitch": "0", "start": 12, "length": 1, "velocity": 80}
      ]
    },
    "hh": {
      "sound": "hh",
      "orbit": 2,
      "gain": 0.6,
      "pan": 0.5,
      "mute": false,
      "solo": false,
      "cutoff": 57122,
      "resonance": 0.3,
      "sequence": [
        {"pitch": "0", "start": 0, "length": 0.5},
        {"pitch": "0", "start": 2, "length": 0.5},
        {"pitch": "0", "start": 4, "length": 0.5},
        {"pitch": "0", "start": 6, "length": 0.5},
        {"pitch": "0", "start": 8, "length": 0.5},
        {"pitch": "0", "start": 10, "length": 0.5},
        {"pitch": "0", "start": 12, "length": 0.5},
        {"pitch": "0", "start": 14, "length": 0.5}
      ]
    }
  },
  "sequences": {}
}
```

## PlaybackStatus

Current state of the playback engine.

```typescript
interface PlaybackStatus {
  playing: boolean;                 // Is engine currently playing?
  playback_state: string;           // "stopped" | "playing" | "paused"
  bpm: number;                      // Current BPM
  position: Position;               // Current playback position
  active_tracks: string[];          // List of track IDs
  has_pending: boolean;             // Are there pending changes?
  scenes: string[];                 // Available scene IDs
  current_scene: string | null;     // Currently active scene
}

interface Position {
  step: number;                     // Current step (0-based)
  beat: number;                     // Current beat (0-based)
  bar: number;                      // Current bar (0-based)
}
```

## TrackInfo

Summary information about a track.

```typescript
interface TrackInfo {
  id: string;                       // Track identifier
  sound: string;                    // Sound/sample name
  orbit: number;                    // SuperDirt orbit
  gain: number;                     // Volume (0.0-1.0)
  pan: number;                      // Stereo pan (0.0-1.0)
  muted: boolean;                   // Is track muted?
  solo: boolean;                    // Is track soloed?
  length: number;                   // Number of events in sequence
}
```

## MIDI Port

Information about available MIDI ports.

```typescript
interface MidiPort {
  name: string;                     // Port name
  is_input: boolean;                // Is this an input port?
  is_output: boolean;               // Is this an output port?
}
```

## Scene

Scenes allow you to switch between different track configurations.

```typescript
interface Scene {
  id: string;                       // Scene identifier
  tracks: Record<string, Track>;    // Track overrides for this scene
}
```

To use scenes, include them in the CompiledSession:

```json
{
  "environment": {"bpm": 120},
  "tracks": {
    "bd": {...},
    "sd": {...}
  },
  "sequences": {},
  "scenes": {
    "intro": {
      "tracks": {
        "bd": {"mute": false},
        "sd": {"mute": true}
      }
    },
    "verse": {
      "tracks": {
        "bd": {"mute": false},
        "sd": {"mute": false}
      }
    }
  }
}
```

Activate a scene with:
```bash
curl -X POST http://localhost:57122/scene/activate \
  -H "Content-Type: application/json" \
  -d '{"scene_id": "intro"}'
```

## SuperDirt Parameters

Oiduna supports all SuperDirt parameters. Common ones include:

### Audio Effects
- `gain` - Volume (0.0-1.0)
- `pan` - Stereo pan (0.0-1.0)
- `cutoff` - Low-pass filter cutoff frequency (Hz)
- `resonance` - Filter resonance (0.0-1.0)
- `delay` - Delay send amount (0.0-1.0)
- `delaytime` - Delay time (seconds)
- `delayfeedback` - Delay feedback (0.0-1.0)
- `reverb` - Reverb send amount (0.0-1.0)
- `room` - Reverb room size (0.0-1.0)

### Playback
- `speed` - Playback speed (1.0 = normal, 2.0 = double speed)
- `begin` - Sample start position (0.0-1.0)
- `end` - Sample end position (0.0-1.0)
- `loop` - Number of loops (integer)

### Synthesis
- `sustain` - Note sustain time (seconds)
- `attack` - Envelope attack time (seconds)
- `release` - Envelope release time (seconds)
- `shape` - Waveshaper amount (0.0-1.0)

Example track with effects:
```json
{
  "bd": {
    "sound": "bd",
    "orbit": 0,
    "gain": 0.8,
    "pan": 0.5,
    "cutoff": 2000,
    "resonance": 0.2,
    "delay": 0.3,
    "delaytime": 0.25,
    "delayfeedback": 0.5,
    "reverb": 0.2,
    "room": 0.8,
    "sequence": [...]
  }
}
```

## Time Units

- **Step**: The smallest rhythmic unit. A 16th note at 4/4 time.
- **Beat**: 4 steps = 1 beat (quarter note)
- **Bar**: 16 steps = 4 beats = 1 bar (measure)

At 120 BPM:
- 1 step = 125ms
- 1 beat = 500ms
- 1 bar = 2000ms (2 seconds)

## Error Responses

All API errors follow this format:

```typescript
interface ErrorResponse {
  detail: string;                   // Error message
}
```

Pydantic validation errors have more detail:

```typescript
interface ValidationError {
  detail: Array<{
    type: string;                   // Error type (e.g., "greater_than")
    loc: string[];                  // Field location
    msg: string;                    // Human-readable message
    input: any;                     // The invalid input value
  }>;
}
```
