# Oiduna Usage Patterns

**Version**: 1.0
**Last Updated**: 2026-02-24

Common patterns and best practices for using Oiduna.

---

## Table of Contents

1. [Basic Patterns](#basic-patterns)
2. [Intermediate Patterns](#intermediate-patterns)
3. [Advanced Patterns](#advanced-patterns)
4. [Anti-Patterns](#anti-patterns)
5. [Troubleshooting](#troubleshooting)

---

## Basic Patterns

### Pattern 1: Simple Loop Playback

**Goal**: Load a pattern and start playback

```bash
# 1. Load session
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
    "tracks_midi": {},
    "mixer_lines": {},
    "scenes": {},
    "apply": null
  }'

# 2. Start playback
curl -X POST http://localhost:57122/playback/start

# 3. Stop when done
curl -X POST http://localhost:57122/playback/stop
```

---

### Pattern 2: Change BPM

**Goal**: Update tempo without reloading session

```bash
# Update BPM to 140
curl -X PATCH http://localhost:57122/playback/environment \
  -H "Content-Type: application/json" \
  -d '{"bpm": 140.0}'
```

**Timing**: Change applies immediately (or use `apply.timing` for synchronized change)

---

### Pattern 3: Mute/Unmute Track

**Goal**: Toggle track playback

```bash
# Mute kick
curl -X POST http://localhost:57122/playback/tracks/kick/mute \
  -H "Content-Type: application/json" \
  -d '{"muted": true}'

# Unmute kick
curl -X POST http://localhost:57122/playback/tracks/kick/mute \
  -H "Content-Type: application/json" \
  -d '{"muted": false}'
```

---

### Pattern 4: Solo Track

**Goal**: Solo one track (mutes all others)

```bash
# Solo snare
curl -X POST http://localhost:57122/playback/tracks/snare/solo \
  -H "Content-Type: application/json" \
  -d '{"solo": true}'

# Unsolo snare
curl -X POST http://localhost:57122/playback/tracks/snare/solo \
  -H "Content-Type: application/json" \
  -d '{"solo": false}'
```

---

### Pattern 5: Update Track Parameters

**Goal**: Change sound parameters in real-time

```bash
# Update kick gain and cutoff
curl -X PATCH http://localhost:57122/playback/tracks/kick/params \
  -H "Content-Type: application/json" \
  -d '{
    "gain": 0.8,
    "cutoff": 2000.0,
    "resonance": 0.3
  }'
```

**Timing**: Changes apply immediately (or use `apply.timing`)

---

## Intermediate Patterns

### Pattern 6: Scene Switching

**Goal**: Switch between different musical sections

**Step 1: Define scenes in session**
```json
{
  "environment": {"bpm": 120},
  "tracks": { ... },
  "sequences": { ... },
  "scenes": {
    "intro": {
      "name": "intro",
      "tracks": {
        "kick": { ... },
        "hihat": { ... }
      },
      "sequences": {
        "kick": { ... },
        "hihat": { ... }
      }
    },
    "verse": {
      "name": "verse",
      "tracks": {
        "kick": { ... },
        "snare": { ... },
        "hihat": { ... }
      },
      "sequences": { ... }
    }
  }
}
```

**Step 2: Activate scene**
```bash
# Switch to verse scene
curl -X POST http://localhost:57122/scene/activate \
  -H "Content-Type: application/json" \
  -d '{"scene_id": "verse", "timing": "bar"}'
```

**Timing Options**:
- `"now"` - Immediate
- `"beat"` - Next beat boundary
- `"bar"` - Next bar boundary (recommended)
- `"seq"` - Next sequence start (step 0)

---

### Pattern 7: MIDI Output

**Goal**: Control external MIDI hardware

**Step 1: List MIDI ports**
```bash
curl http://localhost:57122/midi/ports
```

**Step 2: Select MIDI port**
```bash
curl -X POST http://localhost:57122/midi/port \
  -H "Content-Type: application/json" \
  -d '{"port_name": "IAC Driver Bus 1"}'
```

**Step 3: Load session with MIDI track**
```json
{
  "environment": {"bpm": 120},
  "tracks": {},
  "tracks_midi": {
    "synth": {
      "track_id": "synth",
      "channel": 0,
      "velocity": 100,
      "transpose": 0,
      "mute": false,
      "solo": false
    }
  },
  "sequences": {
    "synth": {
      "track_id": "synth",
      "events": [
        {"step": 0, "note": 60, "velocity": 1.0},
        {"step": 4, "note": 64, "velocity": 0.8},
        {"step": 8, "note": 67, "velocity": 0.9}
      ]
    }
  }
}
```

---

### Pattern 8: SuperDirt Sample Loading

**Goal**: Use custom audio samples

**Step 1: Upload sample**
```bash
curl -X POST http://localhost:57122/assets/samples \
  -F "file=@my_kick.wav" \
  -F "category=kicks"
```

**Step 2: Use in pattern**
```json
{
  "tracks": {
    "custom_kick": {
      "params": {
        "s": "kicks",
        "n": 0,
        "gain": 1.0
      }
    }
  }
}
```

---

### Pattern 9: Real-time Trigger

**Goal**: Manually trigger sounds (MIDI controller, UI button)

```bash
# Trigger OSC sound immediately
curl -X POST http://localhost:57122/playback/trigger/osc \
  -H "Content-Type: application/json" \
  -d '{"track_id": "kick", "velocity": 1.0}'

# Trigger MIDI note immediately
curl -X POST http://localhost:57122/playback/trigger/midi \
  -H "Content-Type: application/json" \
  -d '{"track_id": "synth", "note": 60, "velocity": 100}'
```

**Use Cases**:
- Live MIDI controller input
- UI button clicks
- External trigger events

---

### Pattern 10: Mixer Routing

**Goal**: Route multiple tracks through bus effects

```json
{
  "tracks": {
    "kick": {
      "params": {"s": "bd", "orbit": 0},
      "sends": [
        {"mixer_line": "drums_bus", "gain": 1.0}
      ]
    },
    "snare": {
      "params": {"s": "sd", "orbit": 0},
      "sends": [
        {"mixer_line": "drums_bus", "gain": 1.0}
      ]
    }
  },
  "mixer_lines": {
    "drums_bus": {
      "name": "drums_bus",
      "include": ["kick", "snare"],
      "volume": 0.9,
      "output": 0,
      "fx": {
        "reverb_send": 0.3,
        "reverb_room": 0.8,
        "delay_send": 0.2,
        "delay_time": 0.375,
        "delay_feedback": 0.4
      }
    }
  }
}
```

**Signal Flow**:
```
kick → drums_bus → reverb/delay → output
snare → drums_bus → reverb/delay → output
```

---

## Advanced Patterns

### Pattern 11: Client Metadata Sharing (B2B)

**Goal**: Synchronize musical context between multiple clients

**Client A (Leader) - Share chord progression**
```bash
curl -X POST http://localhost:57122/session/clients/alice_mars/metadata \
  -H "Content-Type: application/json" \
  -d '{
    "scale": "C_major",
    "chords": ["Cmaj7", "Dm7", "G7", "Cmaj7"],
    "chord_position": 0,
    "message": "Starting II-V-I in C"
  }'
```

**Client B (Follower) - Read metadata**
```bash
# Get all clients
curl http://localhost:57122/session/clients

# Get specific client
curl http://localhost:57122/session/clients/alice_mars
```

**Client B - Follow chord changes via SSE**
```javascript
const eventSource = new EventSource('http://localhost:57122/stream');

eventSource.addEventListener('client_metadata_updated', (e) => {
  const update = JSON.parse(e.data);
  if (update.client_id === 'alice_mars') {
    const chordPos = update.metadata.chord_position;
    // Update own pattern to match chord
  }
});
```

---

### Pattern 12: Micro-timing (Triplets, Swing)

**Goal**: Sub-step timing precision

**8th Note Triplets**
```python
# 1 beat = 500ms @ 120 BPM
triplet_interval = 500 / 3  # 166.67ms

events = [
    {"step": 0, "offset_ms": 0.0, "velocity": 1.0},
    {"step": 0, "offset_ms": 166.67, "velocity": 0.8},
    {"step": 0, "offset_ms": 333.33, "velocity": 0.8}
]
```

**Swing**
```python
swing_ms = 20.0

events = [
    {"step": 0, "offset_ms": 0.0},        # On-beat
    {"step": 1, "offset_ms": swing_ms},   # Delayed
    {"step": 2, "offset_ms": 0.0},        # On-beat
    {"step": 3, "offset_ms": swing_ms}    # Delayed
]
```

**Flam**
```python
events = [
    {"step": 0, "offset_ms": -5.0, "velocity": 0.3},  # Ghost (5ms early)
    {"step": 0, "offset_ms": 0.0, "velocity": 1.0}    # Main
]
```

---

### Pattern 13: Timing Control

**Goal**: Synchronize pattern updates to musical boundaries

**Apply at next bar**
```bash
curl -X POST http://localhost:57122/playback/session \
  -H "Content-Type: application/json" \
  -d '{
    "data": { ... },
    "apply": {
      "timing": "bar"
    }
  }'
```

**Apply at specific step**
```bash
curl -X POST http://localhost:57122/playback/session \
  -H "Content-Type: application/json" \
  -d '{
    "data": { ... },
    "apply": {
      "timing": "absolute",
      "step": 128
    }
  }'
```

---

### Pattern 14: Multiple Events per Step

**Goal**: Play multiple sounds simultaneously

```json
{
  "sequences": {
    "percussion": {
      "track_id": "percussion",
      "events": [
        {"step": 0, "note": 60, "velocity": 1.0},
        {"step": 0, "note": 64, "velocity": 0.8},
        {"step": 0, "note": 67, "velocity": 0.8}
      ]
    }
  }
}
```

**Result**: All three notes trigger at step 0 (chord)

---

### Pattern 15: SSE Event Streaming

**Goal**: React to playback state in real-time

```javascript
const eventSource = new EventSource('http://localhost:57122/stream');

// Position updates
eventSource.addEventListener('position', (e) => {
  const pos = JSON.parse(e.data);
  updateUI(pos.step, pos.beat, pos.bar);
});

// Status changes
eventSource.addEventListener('status', (e) => {
  const status = JSON.parse(e.data);
  if (status.playing) {
    showPlayButton(false);
  } else {
    showPlayButton(true);
  }
});

// Client metadata updates
eventSource.addEventListener('client_metadata_updated', (e) => {
  const update = JSON.parse(e.data);
  updateCollaboratorInfo(update.client_id, update.metadata);
});
```

---

## Anti-Patterns

### ❌ Anti-Pattern 1: Frequent Session Reloads

**Bad**:
```bash
# Reloading entire session for minor changes
curl -X POST /playback/session -d @session.json  # Expensive!
```

**Good**:
```bash
# Use parameter updates instead
curl -X PATCH /playback/tracks/kick/params -d '{"gain": 0.8}'
```

**Why**: Session load rebuilds step indices (~10-100ms). Parameter updates are faster (~1ms).

---

### ❌ Anti-Pattern 2: Polling for Status

**Bad**:
```javascript
setInterval(() => {
  fetch('/playback/status').then(r => r.json()).then(updateUI);
}, 100);  // Polling every 100ms!
```

**Good**:
```javascript
const eventSource = new EventSource('/stream');
eventSource.addEventListener('position', (e) => {
  updateUI(JSON.parse(e.data));
});
```

**Why**: SSE is push-based, no polling overhead.

---

### ❌ Anti-Pattern 3: Ignoring Timing Control

**Bad**:
```bash
curl -X POST /playback/session -d @new_pattern.json
# Pattern changes mid-bar, sounds glitchy
```

**Good**:
```bash
curl -X POST /playback/session -d '{
  "data": {...},
  "apply": {"timing": "bar"}
}'
```

**Why**: Musical synchronization prevents glitches.

---

### ❌ Anti-Pattern 4: Sparse Events Without Step Index

**Bad** (if you implement custom Distribution):
```python
# Linear search through all events
for event in all_events:
    if event.step == current_step:
        process(event)
```

**Good**:
```python
# Use EventSequence.from_events (builds index)
sequence = EventSequence.from_events(track_id, events)
events_at_step = sequence.get_events_at(current_step)  # O(1)
```

**Why**: O(1) lookup vs O(N) search.

---

### ❌ Anti-Pattern 5: Forgetting to Clean Up Client Metadata

**Bad**:
```bash
# Register client but never clean up on disconnect
curl -X POST /session/clients/user_alice/metadata -d '{...}'
# (client disconnects, metadata stays forever)
```

**Good**:
```bash
# On disconnect
curl -X DELETE /session/clients/user_alice
```

**Why**: Prevents stale metadata accumulation.

---

## Troubleshooting

### Issue 1: No Sound Output

**Symptoms**: Session loads, playback starts, but no audio

**Diagnosis**:
```bash
# Check SuperDirt is running
lsof -i :57120  # Should show sclang

# Check playback status
curl http://localhost:57122/playback/status
# → "playing": true?

# Check tracks
curl http://localhost:57122/tracks
# → Any tracks listed?
```

**Solutions**:
1. Restart SuperDirt (`sclang`)
2. Check OSC port: `OSC_PORT=57120` (default)
3. Check track not muted: `"mute": false`
4. Check gain > 0: `"gain": 1.0`

---

### Issue 2: Timing Drift

**Symptoms**: Pattern drifts out of sync over time

**Diagnosis**:
```bash
# Check system clock
timedatectl  # (Linux)
# Or: systemsetup -getnetworktimeserver  # (macOS)
```

**Solutions**:
1. Enable NTP time sync
2. Restart Oiduna (resets anchor time)
3. Report as bug (should not occur with anchor-based timing)

---

### Issue 3: MIDI Not Working

**Symptoms**: MIDI track defined, but no MIDI output

**Diagnosis**:
```bash
# List MIDI ports
curl http://localhost:57122/midi/ports

# Check selected port
# (Look in Oiduna logs for current port)
```

**Solutions**:
1. Select correct port: `POST /midi/port`
2. Check MIDI cable connected
3. Check MIDI channel matches (0-15)
4. Try MIDI panic: `POST /midi/panic`

---

### Issue 4: High CPU Usage

**Symptoms**: CPU > 50% for simple pattern

**Diagnosis**:
```bash
# Check metrics
curl http://localhost:57122/metrics

# Check session size
curl http://localhost:57122/playback/status | jq '.active_tracks | length'
```

**Solutions**:
1. Reduce concurrent events per step (< 50)
2. Reduce total tracks (< 20 for typical use)
3. Lower BPM (< 180)
4. Close other applications

---

### Issue 5: Client Metadata Not Updating

**Symptoms**: SSE not receiving `client_metadata_updated` events

**Diagnosis**:
```bash
# Check SSE connection
curl -N http://localhost:57122/stream
# Should see heartbeat events

# Check client registered
curl http://localhost:57122/session/clients
```

**Solutions**:
1. Ensure SSE connection active
2. Check client_id matches
3. Verify metadata POST succeeded (200 response)

---

### Issue 6: Pattern Cuts Off Early

**Symptoms**: Only first few bars play, then silence

**Diagnosis**: Likely using wrong step range

**Solution**: Ensure events use steps 0-255 (not 0-15)
```json
{
  "events": [
    {"step": 0, ...},
    {"step": 4, ...},
    {"step": 8, ...},
    {"step": 12, ...},
    {"step": 16, ...},  // Continue to 255!
    ...
  ]
}
```

---

## Best Practices Summary

### ✅ Do:
- Use timing control (`apply.timing`) for synchronized changes
- Use SSE for real-time updates (not polling)
- Clean up client metadata on disconnect
- Use parameter updates for minor changes (not full session reload)
- Keep events per step < 50 for best performance

### ❌ Don't:
- Poll `/playback/status` frequently (use SSE)
- Reload entire session for minor parameter changes
- Forget to set `apply.timing` for pattern changes
- Create > 100 tracks in one session
- Leave stale client metadata

---

**Document Version**: 1.0
**Last Updated**: 2026-02-24
**Next Review**: Based on user feedback
