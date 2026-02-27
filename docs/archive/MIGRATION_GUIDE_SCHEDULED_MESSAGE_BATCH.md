# Migration Guide: CompiledSession → ScheduledMessageBatch

**Date**: 2026-02-26
**Breaking Change**: Complete architecture unification

## Overview

Oiduna has completely transitioned to the ScheduledMessageBatch architecture. The CompiledSession format and all related infrastructure have been removed.

## What Was Removed

### IR Models
- `CompiledSession`, `ApplyCommand`, `ApplyTiming`
- `Track`, `TrackParams`, `FxParams`, `TrackFxParams`, `TrackMeta`
- `EventSequence`, `Event`
- `Environment`, `Chord`
- `MixerLine`, `MixerLineFx`, `MixerLineDynamics`
- `Scene`
- `TrackMidi`
- `Send`

### API Endpoints
- `POST /playback/pattern` (CompiledSession endpoint)
- `POST /scene/activate`
- `GET /scenes`

### LoopEngine Methods
- `_handle_compile()`
- `_handle_scene()`, `_handle_scenes()`
- `compile()`, `activate_scene()` public API methods

### RuntimeState Methods
- `load_compiled_session()`, `get_effective_session()`
- `apply_scene()`, `apply_override()`
- `set_pending_change()`, `_apply_partial()`
- Deep merge logic (`_deep_merge`, `_merge_environment`, `_merge_track`, etc.)

## What Remains

### API Endpoints
- `POST /playback/session` - **ONLY endpoint for loading patterns**
- `POST /playback/start`, `/playback/stop`, `/playback/pause`
- `POST /playback/bpm`
- `POST /tracks/{id}/mute`, `POST /tracks/{id}/solo`
- `GET /playback/status`

### RuntimeState
- Playback state management (`playing`, `position`)
- BPM management (`bpm`, `set_bpm()`)
- Mute/Solo filtering (`set_track_mute()`, `set_track_solo()`, `filter_messages()`)

## Migration Steps

### 1. Update Compiler Output

**Before (CompiledSession)**:
```python
def compile_dsl_to_session(dsl_code: str) -> dict:
    """Old compiler output"""
    return {
        "environment": {
            "bpm": 120.0,
            "scale": "C_major",
            "default_gate": 1.0,
            "swing": 0.0,
        },
        "tracks": {
            "kick": {
                "meta": {
                    "track_id": "kick",
                    "mute": False,
                    "solo": False,
                },
                "params": {
                    "s": "bd",
                    "gain": 0.8,
                    "pan": 0.5,
                },
                "fx": {
                    "room": 0.3,
                },
            },
        },
        "sequences": {
            "kick": {
                "track_id": "kick",
                "events": [
                    {"step": 0, "velocity": 1.0},
                    {"step": 4, "velocity": 0.8},
                    {"step": 8, "velocity": 1.0},
                    {"step": 12, "velocity": 0.8},
                ],
            },
        },
    }
```

**After (ScheduledMessageBatch)**:
```python
def compile_dsl_to_batch(dsl_code: str) -> dict:
    """New compiler output"""
    return {
        "messages": [
            {
                "destination_id": "superdirt",
                "cycle": 0.0,
                "step": 0,
                "params": {
                    "track_id": "kick",  # REQUIRED for mute/solo
                    "s": "bd",
                    "gain": 0.8,         # velocity already applied
                    "pan": 0.5,
                    "room": 0.3,
                },
            },
            {
                "destination_id": "superdirt",
                "cycle": 1.0,
                "step": 4,
                "params": {
                    "track_id": "kick",
                    "s": "bd",
                    "gain": 0.64,        # 0.8 * 0.8 velocity
                    "pan": 0.5,
                    "room": 0.3,
                },
            },
            # ... more messages
        ],
        "bpm": 120.0,
        "pattern_length": 4.0,  # in cycles
    }
```

### 2. Handle Scene Expansion (Client-Side)

Scenes are no longer managed by Oiduna. You must expand scenes before sending.

**Before**:
```python
# Server-side scene management
POST /playback/pattern
{
    "scenes": {
        "verse": {...},
        "chorus": {...},
    }
}

POST /scene/activate
{
    "scene_id": "verse"
}
```

**After**:
```python
# Client-side scene expansion
def activate_scene(scene_name: str):
    """Expand scene and send as message batch"""
    scene_data = scenes[scene_name]
    message_batch = compile_scene_to_batch(scene_data)

    POST /playback/session
    {
        "messages": message_batch["messages"],
        "bpm": message_batch["bpm"],
        "pattern_length": message_batch["pattern_length"],
    }
```

### 3. Handle Apply Timing (Client-Side)

Apply timing is no longer managed by Oiduna. You must decide when to send patterns.

**Before**:
```python
# Server-side timing
POST /playback/pattern
{
    "tracks": {...},
    "sequences": {...},
    "apply": {
        "timing": "bar",          # Server decides when to apply
        "track_ids": ["kick"],    # Server filters tracks
    }
}
```

**After**:
```python
# Client-side timing
import time
import asyncio

async def apply_at_bar(message_batch: dict):
    """Wait for next bar boundary before sending"""
    # Get current position
    status = requests.get("/playback/status").json()
    step = status["position"]["step"]

    # Calculate wait time until next bar (step 0, 16, 32, ...)
    steps_until_bar = (16 - (step % 16)) % 16
    wait_seconds = steps_until_bar * status["bpm"] / 60 / 4

    await asyncio.sleep(wait_seconds)

    # Send at bar boundary
    POST /playback/session
    {
        "messages": message_batch["messages"],
        "bpm": message_batch["bpm"],
        "pattern_length": message_batch["pattern_length"],
    }
```

### 4. Add track_id to All Messages

The `track_id` parameter is **required** for mute/solo filtering.

**Before**:
```python
# track_id was in Track metadata
"tracks": {
    "kick": {
        "meta": {"track_id": "kick"},
        "params": {"s": "bd"},
    }
}
```

**After**:
```python
# track_id must be in every message params
{
    "destination_id": "superdirt",
    "cycle": 0.0,
    "step": 0,
    "params": {
        "track_id": "kick",  # REQUIRED
        "s": "bd",
    }
}
```

**Important**:
- Messages without `track_id` will **always** be sent (not affected by mute/solo)
- Use this for global effects or messages that should never be muted

### 5. Update Mute/Solo Logic

Mute/Solo now filters messages at send time.

**Before**:
```python
# RuntimeState stored track mute/solo in metadata
track.meta.mute = True
```

**After**:
```python
# RuntimeState filters messages by track_id
POST /tracks/kick/mute  # Sets mute state

# In _step_loop(), messages are filtered:
scheduled_messages = state.filter_messages(scheduled_messages)
```

**API remains the same**:
```bash
# Mute a track
curl -X POST http://localhost:8000/tracks/kick/mute

# Unmute a track
curl -X DELETE http://localhost:8000/tracks/kick/mute

# Solo a track
curl -X POST http://localhost:8000/tracks/kick/solo

# Unsolo a track
curl -X DELETE http://localhost:8000/tracks/kick/solo
```

## Example: Complete Migration

### Old MARS Compiler Flow

```python
class MARSCompiler:
    def compile(self, dsl_code: str) -> dict:
        # Parse DSL
        ast = parse(dsl_code)

        # Generate CompiledSession
        session = {
            "environment": self._compile_environment(ast),
            "tracks": self._compile_tracks(ast),
            "sequences": self._compile_sequences(ast),
            "scenes": self._compile_scenes(ast),
        }

        # Send to Oiduna
        requests.post(
            "http://localhost:8000/playback/pattern",
            json=session
        )
```

### New MARS Compiler Flow

```python
class MARSCompiler:
    def compile(self, dsl_code: str) -> dict:
        # Parse DSL
        ast = parse(dsl_code)

        # Extract metadata
        bpm = ast.environment.bpm
        pattern_length = ast.environment.pattern_length

        # Generate messages directly
        messages = []
        for track in ast.tracks:
            for event in track.sequence.events:
                # Calculate cycle position
                cycle = event.step / (pattern_length * 16)  # 16 steps per cycle

                # Create message with merged params
                msg = {
                    "destination_id": track.destination_id,
                    "cycle": cycle,
                    "step": event.step,
                    "params": {
                        "track_id": track.track_id,  # REQUIRED
                        **track.params.to_dict(),    # Merge track params
                        **track.fx.to_dict(),        # Merge FX params
                        "gain": track.params.gain * event.velocity,  # Apply velocity
                    }
                }

                # Add optional params
                if event.note is not None:
                    msg["params"]["note"] = event.note
                if event.gate is not None:
                    msg["params"]["sustain"] = event.gate

                messages.append(msg)

        # Create batch
        batch = {
            "messages": messages,
            "bpm": bpm,
            "pattern_length": pattern_length,
        }

        # Send to Oiduna
        requests.post(
            "http://localhost:8000/playback/session",
            json=batch
        )
```

## Status Response Changes

**Old Response**:
```json
{
    "playing": true,
    "playback_state": "playing",
    "bpm": 120.0,
    "position": {"step": 0, "bar": 0, "beat": 0},
    "active_tracks": ["kick", "hihat"],
    "has_pending": false,
    "scenes": ["verse", "chorus"],
    "current_scene": "verse"
}
```

**New Response**:
```json
{
    "playing": true,
    "playback_state": "playing",
    "bpm": 120.0,
    "position": {"step": 0, "bar": 0, "beat": 0},
    "active_tracks": ["kick", "hihat"],
    "known_tracks": ["kick", "hihat", "snare"],
    "muted_tracks": ["snare"],
    "soloed_tracks": []
}
```

## Testing Changes

### Old Test (CompiledSession)
```python
def test_load_session(test_engine):
    session = {
        "environment": {"bpm": 120.0},
        "tracks": {"kick": {...}},
        "sequences": {"kick": {...}},
    }

    result = test_engine._handle_compile(session)
    assert result.success
    assert test_engine.state.bpm == 120.0
```

### New Test (ScheduledMessageBatch)
```python
def test_load_session(test_engine):
    batch = {
        "messages": [
            {
                "destination_id": "superdirt",
                "cycle": 0.0,
                "step": 0,
                "params": {"track_id": "kick", "s": "bd"},
            }
        ],
        "bpm": 120.0,
        "pattern_length": 4.0,
    }

    result = test_engine._handle_session(batch)
    assert result.success
    assert test_engine.state.bpm == 120.0
    assert "kick" in test_engine.state._known_track_ids
```

## Benefits of This Change

1. **Dramatic Simplification**
   - Removed 20+ files and 500+ lines of code
   - RuntimeState: 624 lines → ~280 lines (75% reduction)

2. **Clear Responsibilities**
   - **MARS/Distribution**: Pattern generation, scene expansion, apply timing
   - **Oiduna**: Message scheduling, destination routing, mute/solo filtering

3. **Better Performance**
   - No deep merging or session caching
   - Direct message scheduling
   - O(n) filtering instead of complex state management

4. **Unified Architecture**
   - One data format throughout the system
   - No conversion layer needed
   - Easier to understand and maintain

## Troubleshooting

### Messages Not Playing
**Problem**: Messages sent but no sound
**Solution**: Ensure `track_id` is in `params` and track is not muted

### Mute/Solo Not Working
**Problem**: Mute/Solo endpoints return 404
**Solution**: Track must be registered first (happens automatically when loading messages)

### All Messages Filtered
**Problem**: No messages sent even though not muted
**Solution**: Check that `track_id` matches exactly with registered tracks (case-sensitive)

## Support

For questions about this migration, please refer to:
- CHANGELOG.md - Full list of changes
- oiduna_loop/state/runtime_state.py - New RuntimeState implementation
- oiduna_loop/engine/loop_engine.py - New LoopEngine implementation
