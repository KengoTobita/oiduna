# Oiduna Distribution Development Guide

This guide explains how to create your own distribution (language frontend) for Oiduna.

## What is a Distribution?

A **distribution** is a frontend language/DSL that compiles to Oiduna's `CompiledSession` format. Examples:
- **MARS** - Pattern language with hierarchical syntax
- **TidalCycles** - Haskell-embedded DSL
- **Strudel** - JavaScript pattern language
- **Your own DSL** - Any language that can generate patterns

## Architecture

```
┌─────────────────┐
│  Your DSL       │  ← User writes code here
└────────┬────────┘
         │ parse & compile
         ↓
┌─────────────────┐
│ CompiledSession │  ← JSON format
└────────┬────────┘
         │ HTTP POST
         ↓
┌─────────────────┐
│  Oiduna API     │  ← Loop engine
└────────┬────────┘
         │ OSC/MIDI
         ↓
┌─────────────────┐
│ SuperDirt/DAW   │  ← Audio output
└─────────────────┘
```

## Quick Start

### 1. Install Oiduna

```bash
# Start Oiduna server
cd oiduna
uv sync
uv run python -m oiduna_api.main
```

Oiduna will be running at `http://localhost:8000`.

### 2. Create Your Distribution

```bash
mkdir my_distribution
cd my_distribution
uv init
```

### 3. Install HTTP Client

```bash
uv add httpx
```

### 4. Create Basic Client

See [Client Example](#python-client-example) below.

## CompiledSession Format

Your compiler must generate JSON in this format:

```typescript
interface CompiledSession {
  environment: {
    bpm: number;
    [key: string]: any;
  };
  tracks: Record<string, Track>;
  sequences: Record<string, Sequence>;
}

interface Track {
  sound: string;
  orbit: number;
  gain: number;
  pan: number;
  mute: boolean;
  solo: boolean;
  sequence: Event[];
  [key: string]: any;  // Additional SuperDirt params
}

interface Event {
  pitch: string;
  start: number;   // Start time in steps (0-based)
  length: number;  // Duration in steps
  velocity?: number;
  [key: string]: any;
}
```

See [data-model.md](data-model.md) for complete reference.

## Python Client Example

```python
"""Basic Oiduna API client"""
import httpx
from typing import Dict, Any

class OidunaClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.Client(base_url=base_url)

    def load_pattern(self, session: Dict[str, Any]) -> bool:
        """Load a compiled session pattern"""
        response = self.client.post("/playback/pattern", json=session)
        response.raise_for_status()
        return response.json()["status"] == "ok"

    def start(self) -> bool:
        """Start playback"""
        response = self.client.post("/playback/start")
        response.raise_for_status()
        return True

    def stop(self) -> bool:
        """Stop playback"""
        response = self.client.post("/playback/stop")
        response.raise_for_status()
        return True

    def set_bpm(self, bpm: float) -> bool:
        """Change BPM"""
        response = self.client.post("/playback/bpm", json={"bpm": bpm})
        response.raise_for_status()
        return True

    def get_status(self) -> Dict[str, Any]:
        """Get current playback status"""
        response = self.client.get("/playback/status")
        response.raise_for_status()
        return response.json()

    def mute_track(self, track_id: str, muted: bool) -> bool:
        """Mute/unmute a track"""
        response = self.client.post(
            f"/tracks/{track_id}/mute",
            json={"muted": muted}
        )
        response.raise_for_status()
        return True

# Usage example
if __name__ == "__main__":
    client = OidunaClient()

    # Create a simple pattern
    session = {
        "environment": {"bpm": 120},
        "tracks": {
            "bd": {
                "sound": "bd",
                "orbit": 0,
                "gain": 1.0,
                "pan": 0.5,
                "mute": False,
                "solo": False,
                "sequence": [
                    {"pitch": "0", "start": 0, "length": 1},
                    {"pitch": "0", "start": 4, "length": 1},
                    {"pitch": "0", "start": 8, "length": 1},
                    {"pitch": "0", "start": 12, "length": 1},
                ]
            }
        },
        "sequences": {}
    }

    # Load and play
    client.load_pattern(session)
    client.start()

    # Check status
    status = client.get_status()
    print(f"Playing: {status['playing']}, BPM: {status['bpm']}")
```

## TypeScript Client Example

```typescript
/**
 * Basic Oiduna API client
 */
interface CompiledSession {
  environment: { bpm: number; [key: string]: any };
  tracks: Record<string, Track>;
  sequences: Record<string, any>;
}

interface Track {
  sound: string;
  orbit: number;
  gain: number;
  pan: number;
  mute: boolean;
  solo: boolean;
  sequence: Event[];
}

interface Event {
  pitch: string;
  start: number;
  length: number;
  velocity?: number;
}

class OidunaClient {
  constructor(private baseUrl: string = "http://localhost:8000") {}

  async loadPattern(session: CompiledSession): Promise<void> {
    const response = await fetch(`${this.baseUrl}/playback/pattern`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(session),
    });

    if (!response.ok) {
      throw new Error(`Failed to load pattern: ${response.statusText}`);
    }
  }

  async start(): Promise<void> {
    await fetch(`${this.baseUrl}/playback/start`, { method: "POST" });
  }

  async stop(): Promise<void> {
    await fetch(`${this.baseUrl}/playback/stop`, { method: "POST" });
  }

  async setBpm(bpm: number): Promise<void> {
    await fetch(`${this.baseUrl}/playback/bpm`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ bpm }),
    });
  }

  async getStatus(): Promise<any> {
    const response = await fetch(`${this.baseUrl}/playback/status`);
    return response.json();
  }

  async muteTrack(trackId: string, muted: boolean): Promise<void> {
    await fetch(`${this.baseUrl}/tracks/${trackId}/mute`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ muted }),
    });
  }

  /**
   * Listen to real-time state updates via SSE
   */
  streamEvents(onEvent: (type: string, data: any) => void): EventSource {
    const eventSource = new EventSource(`${this.baseUrl}/stream`);

    eventSource.addEventListener("position", (e) => {
      onEvent("position", JSON.parse(e.data));
    });

    eventSource.addEventListener("status", (e) => {
      onEvent("status", JSON.parse(e.data));
    });

    return eventSource;
  }
}

// Usage example
const client = new OidunaClient();

const session: CompiledSession = {
  environment: { bpm: 120 },
  tracks: {
    bd: {
      sound: "bd",
      orbit: 0,
      gain: 1.0,
      pan: 0.5,
      mute: false,
      solo: false,
      sequence: [
        { pitch: "0", start: 0, length: 1 },
        { pitch: "0", start: 4, length: 1 },
      ],
    },
  },
  sequences: {},
};

await client.loadPattern(session);
await client.start();

// Listen to events
const eventSource = client.streamEvents((type, data) => {
  console.log(`Event: ${type}`, data);
});
```

## Distribution Architecture Patterns

### Pattern 1: Web-Based Editor

```
┌─────────────────────────────┐
│  Monaco Editor (Browser)    │
│  - Syntax highlighting      │
│  - Auto-completion          │
│  - Live compilation         │
└──────────┬──────────────────┘
           │ WebSocket/HTTP
           ↓
┌─────────────────────────────┐
│  Distribution API Server    │
│  - Parse DSL                │
│  - Compile to CompiledSession │
│  - Forward to Oiduna        │
└──────────┬──────────────────┘
           │ HTTP
           ↓
┌─────────────────────────────┐
│  Oiduna API                 │
└─────────────────────────────┘
```

### Pattern 2: CLI Tool

```
┌─────────────────────────────┐
│  User's Terminal            │
│  $ mydsl run pattern.dsl    │
└──────────┬──────────────────┘
           │
           ↓
┌─────────────────────────────┐
│  CLI Compiler               │
│  - Read file                │
│  - Parse & compile          │
│  - Send to Oiduna           │
└──────────┬──────────────────┘
           │ HTTP
           ↓
┌─────────────────────────────┐
│  Oiduna API                 │
└─────────────────────────────┘
```

### Pattern 3: Plugin/Library

```
┌─────────────────────────────┐
│  Host Application (DAW)     │
│  - VST/AU plugin            │
│  - Embeds your DSL runtime  │
└──────────┬──────────────────┘
           │ In-process
           ↓
┌─────────────────────────────┐
│  DSL Compiler Library       │
│  - Compiles on-the-fly      │
│  - Sends HTTP to Oiduna     │
└──────────┬──────────────────┘
           │ HTTP
           ↓
┌─────────────────────────────┐
│  Oiduna API                 │
└─────────────────────────────┘
```

## Real-Time Features

### Server-Sent Events (SSE)

Listen to real-time state updates:

```python
import httpx

def stream_oiduna_events():
    with httpx.stream("GET", "http://localhost:8000/stream") as response:
        for line in response.iter_lines():
            if line.startswith("event:"):
                event_type = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data = json.loads(line.split(":", 1)[1])
                handle_event(event_type, data)

def handle_event(event_type, data):
    if event_type == "position":
        print(f"Step: {data['step']}, Beat: {data['beat']}")
    elif event_type == "status":
        print(f"Playing: {data['playing']}")
```

### Event Types

- `connected` - Initial connection
- `position` - Playback position updates
- `status` - State changes (playing/stopped/paused)
- `tracks` - Track list changes
- `error` - Engine errors
- `heartbeat` - Keep-alive (every 15s)

## Compiler Implementation Tips

### 1. Start Simple

Begin with a minimal DSL that compiles to a single track:

```python
def compile_simple_pattern(pattern: str) -> dict:
    """x8888 → kick on steps 0,4,8,12"""
    events = []
    for i, char in enumerate(pattern):
        if char == "x":
            events.append({
                "pitch": "0",
                "start": i * 4,  # 4 steps apart
                "length": 1
            })

    return {
        "environment": {"bpm": 120},
        "tracks": {
            "bd": {
                "sound": "bd",
                "orbit": 0,
                "gain": 1.0,
                "pan": 0.5,
                "mute": False,
                "solo": False,
                "sequence": events
            }
        },
        "sequences": {}
    }
```

### 2. Add Parser

Use Lark, ANTLR, or a hand-written parser:

```python
from lark import Lark, Transformer

grammar = """
    start: track+
    track: WORD "=" pattern
    pattern: /[x.]+/

    %import common.WORD
    %import common.WS
    %ignore WS
"""

parser = Lark(grammar)

class PatternCompiler(Transformer):
    def start(self, tracks):
        return {
            "environment": {"bpm": 120},
            "tracks": {t["id"]: t for t in tracks},
            "sequences": {}
        }

    def track(self, items):
        track_id = str(items[0])
        pattern = str(items[1])

        events = []
        for i, char in enumerate(pattern):
            if char == "x":
                events.append({
                    "pitch": "0",
                    "start": i,
                    "length": 1
                })

        return {
            "id": track_id,
            "sound": track_id,
            "orbit": 0,
            "gain": 1.0,
            "pan": 0.5,
            "mute": False,
            "solo": False,
            "sequence": events
        }

# Usage
dsl_code = """
bd = x...x...x...x...
sd = ....x.......x...
"""

tree = parser.parse(dsl_code)
session = PatternCompiler().transform(tree)
```

### 3. Add Error Handling

```python
from pydantic import ValidationError

try:
    response = client.post("/playback/pattern", json=session)
    response.raise_for_status()
except ValidationError as e:
    print("Invalid session format:")
    for error in e.errors():
        print(f"  - {error['loc']}: {error['msg']}")
except httpx.HTTPStatusError as e:
    print(f"Oiduna error: {e.response.json()['detail']}")
```

## Testing Your Distribution

### Unit Tests

```python
import pytest

def test_simple_pattern():
    result = compile_pattern("x8888")
    assert result["tracks"]["bd"]["sequence"][0]["start"] == 0
    assert len(result["tracks"]["bd"]["sequence"]) == 4

def test_multiple_tracks():
    dsl = """
    bd = x...x...
    sd = ....x...
    """
    result = compile_dsl(dsl)
    assert "bd" in result["tracks"]
    assert "sd" in result["tracks"]
```

### Integration Tests

```python
def test_with_oiduna():
    client = OidunaClient()
    session = compile_pattern("x8888")

    # Should load successfully
    assert client.load_pattern(session)

    # Should start playing
    assert client.start()

    # Should show playing status
    status = client.get_status()
    assert status["playing"] == True
```

## Example Distributions

### MARS (Reference Implementation)

See `/home/tobita/study/livecoding/MARS_for_oiduna` for the reference MARS distribution.

Key features:
- Lark-based parser
- Hierarchical pattern syntax
- Monaco editor integration
- Real-time compilation API

### TidalCycles Adapter (Example)

```haskell
-- Hypothetical TidalCycles → Oiduna adapter
module OidunaAdapter where

import qualified Network.HTTP.Simple as HTTP

compileAndSend :: Pattern -> IO ()
compileAndSend pattern = do
  let session = toCompiledSession pattern
  let request = HTTP.setRequestBodyJSON session $
                HTTP.parseRequest_ "POST http://localhost:8000/playback/pattern"
  _ <- HTTP.httpJSON request
  return ()

toCompiledSession :: Pattern -> CompiledSession
toCompiledSession p = CompiledSession
  { environment = Env { bpm = 120 }
  , tracks = extractTracks p
  , sequences = mempty
  }
```

## Common Patterns

### Live Coding Loop

```python
def live_coding_loop(evaluate_fn, client):
    """REPL-style live coding"""
    while True:
        code = input(">>> ")
        try:
            session = evaluate_fn(code)
            client.load_pattern(session)
            if not client.get_status()["playing"]:
                client.start()
        except Exception as e:
            print(f"Error: {e}")
```

### Hot Reload

```python
import watchdog

class PatternReloader(FileSystemEventHandler):
    def __init__(self, client, compiler):
        self.client = client
        self.compiler = compiler

    def on_modified(self, event):
        if event.src_path.endswith(".dsl"):
            with open(event.src_path) as f:
                code = f.read()

            session = self.compiler.compile(code)
            self.client.load_pattern(session)
            print(f"Reloaded: {event.src_path}")

# Usage
observer = Observer()
observer.schedule(PatternReloader(client, compiler), path="./patterns")
observer.start()
```

## Resources

- [API Examples](api-examples.md) - Complete API reference
- [Data Model](data-model.md) - CompiledSession schema
- [SuperDirt Docs](https://tidalcycles.org/docs/patternlib/tutorials/superdirt) - Audio parameters
- Oiduna Interactive Docs: http://localhost:8000/docs

## Support

- GitHub Issues: https://github.com/your-org/oiduna/issues
- Discussions: https://github.com/your-org/oiduna/discussions

## Next Steps

1. **Study the API** - Read [api-examples.md](api-examples.md)
2. **Create a minimal compiler** - Start with simple patterns
3. **Add features incrementally** - Parser, effects, scenes
4. **Build a UI** - Web editor, CLI, or plugin
5. **Share your distribution** - Help grow the ecosystem!
