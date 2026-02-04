# GIL Performance Mitigation Strategy

## Executive Summary

Oiduna Core's single-process architecture (Phase 1) may encounter audio dropouts due to Python's Global Interpreter Lock (GIL) when heavy processing occurs alongside real-time audio output. This document outlines the problem, historical context, and mitigation strategies for Phase 2+.

---

## Problem Description

### What is the GIL?

Python's Global Interpreter Lock (GIL) ensures that only one thread executes Python bytecode at a time, even on multi-core systems. This means:

- **CPU-bound tasks block all other threads** in the same process
- Heavy operations (DSL parsing, JSON serialization) can freeze the event loop
- Real-time audio output requires consistent ~4ms precision

### Impact on Live Coding

**Timing Requirements:**
- BPM 120, 256 steps = 8 second loop
- 1 step = ~31ms (at 16 steps per beat)
- **Audio dropout threshold: >10ms delay**

**Heavy Operations in Live Coding:**
```
DSL Parsing:        100-200ms  (complex patterns with modulation)
IR Compilation:      50-100ms  (scale resolution, modulation building)
JSON Serialization:  20-50ms   (large session data)
```

**Result:**
- DSL parse taking 200ms = **6 steps worth of delay**
- Loop engine freezes during parse
- Audible glitches, timing drift

---

## Historical Context: MARS Design

### Original MARS Architecture (ZeroMQ + Multi-Process)

```
┌─────────────────────────────────┐
│   MARS API (Process 1)          │
│                                 │
│  ┌──────────────────────────┐  │
│  │ FastAPI Server           │  │
│  │  - Monaco Editor UI      │  │
│  │  - DSL Input             │  │
│  └──────────┬───────────────┘  │
│             │                   │
│  ┌──────────▼───────────────┐  │
│  │ DSL Parser & Compiler    │  │  ← Heavy processing here
│  │  - Lark parsing (100ms)  │  │     (doesn't affect audio)
│  │  - IR compilation (50ms) │  │
│  └──────────┬───────────────┘  │
│             │                   │
└─────────────┼───────────────────┘
              │
              │ ZeroMQ IPC (msgpack, non-blocking)
              │
┌─────────────▼───────────────────┐
│   MARS Loop (Process 2)         │
│                                 │
│  ┌──────────────────────────┐  │
│  │ Loop Engine              │  │  ← Dedicated GIL
│  │  - 256-step sequencer    │  │     (never blocked)
│  │  - 4ms precision timing  │  │
│  │  - Step processor        │  │
│  └──────────┬───────────────┘  │
│             │                   │
│      ┌──────┴──────┐           │
│      ▼             ▼           │
│    OSC           MIDI          │
│ (SuperDirt)    (Hardware)      │
└─────────────────────────────────┘
```

**Key Design Decision:**
- **Process 1 (API):** Heavy DSL processing with its own GIL
- **Process 2 (Loop):** Dedicated GIL for real-time audio
- **ZeroMQ:** Non-blocking message passing (no shared memory)

**Why This Worked:**
1. DSL parsing in Process 1 doesn't block Process 2
2. Each process has independent GIL
3. Message passing is asynchronous
4. Loop engine guaranteed consistent timing

---

## Current Oiduna Design (Phase 1)

### Single-Process Architecture

```
┌─────────────────────────────────────────────┐
│   Oiduna Core (Single Process)              │
│                                             │
│  ┌──────────────┐      ┌─────────────────┐ │
│  │ FastAPI      │      │ Loop Engine     │ │
│  │              │      │                 │ │
│  │ /playback/   │      │ - 256 steps     │ │
│  │  pattern     │      │ - 4ms precision │ │
│  │              │◄─────┤                 │ │
│  │ (IR only)    │      │ tick() every    │ │
│  │              │      │ ~31ms           │ │
│  └──────────────┘      └─────────────────┘ │
│         │                       │           │
│         └───────────GIL──────────┘          │
│              (shared lock)                  │
└─────────────────────────────────────────────┘
```

**Phase 1 Status: ✅ No Problem**
- Oiduna Core receives **pre-compiled IR** (JSON)
- No heavy DSL parsing in this process
- JSON deserialization is fast (~10ms)
- GIL contention is minimal

**Phase 2+ Risk: ⚠️ Potential Issue**
If heavy processing moves to Oiduna Core:
- Real-time parameter updates
- On-the-fly IR modification
- Complex state calculations
→ These could block the loop engine

---

## Benchmark Data

### Measured Operation Times (Original MARS)

| Operation                    | Time     | Impact (steps @ 120 BPM) |
|------------------------------|----------|--------------------------|
| JSON deserialization (IR)    | ~10ms    | 0.3 steps (acceptable)   |
| DSL parsing (complex)        | 100-200ms| 3-6 steps (glitch!)      |
| IR compilation               | 50-100ms | 1.5-3 steps (glitch!)    |
| Session state deep copy      | 5-15ms   | 0.5 steps (acceptable)   |
| OSC message send (single)    | 0.1ms    | negligible               |
| MIDI message send (single)   | 0.2ms    | negligible               |

**Conclusion:**
- IR reception (current Oiduna): ✅ Safe (<10ms)
- DSL processing in same process: ❌ Dangerous (100ms+)

### Test Environment
- CPU: Modern x86_64 (4+ cores)
- Python: 3.13
- Workload: 8 tracks, 256-step sequences with modulation

---

## Mitigation Strategies

### Strategy 1: Keep Heavy Processing External (Recommended for Phase 2)

**Approach:**
- DSL compilation stays in **Distribution process**
- Oiduna Core receives **lightweight IR only**
- No code changes needed in Oiduna Core

```
┌─────────────────────────┐
│ MARS Distribution       │ (Separate process)
│                         │
│  DSL → Parser → IR      │ ← Heavy work here
│         (200ms)         │
└────────────┬────────────┘
             │
             │ HTTP POST (compiled IR, JSON)
             │
┌────────────▼────────────┐
│ Oiduna Core             │ (Single process, lightweight)
│                         │
│  IR → Engine → Audio    │ ← Fast (~10ms)
│                         │
└─────────────────────────┘
```

**Pros:**
- ✅ No changes to current architecture
- ✅ Maintains single-process simplicity
- ✅ Distribution handles optimization (could use Rust, etc.)
- ✅ Aligns with "language-agnostic" design

**Cons:**
- Distribution must implement compilation
- Can't do real-time DSL eval in Oiduna itself

**Implementation:**
- Phase 2: MARS Distribution implements DSL → IR compilation
- Oiduna Core remains as-is

---

### Strategy 2: Multi-Process Loop Engine (Recommended for Phase 3+)

**Approach:**
- Move loop engine to **dedicated process**
- Use `multiprocessing.Queue` for IPC
- API process can do heavy work without affecting audio

```
┌─────────────────────────────┐
│ Oiduna API Process          │
│                             │
│  FastAPI + Heavy Processing │ ← Can be slow, no problem
│                             │
└────────────┬────────────────┘
             │
             │ multiprocessing.Queue
             │ (load_session, start, stop)
             │
┌────────────▼────────────────┐
│ Oiduna Engine Process       │
│                             │
│  Loop Engine (dedicated)    │ ← Dedicated GIL, never blocks
│  - tick() every 31ms        │
│  - OSC/MIDI output          │
│                             │
└─────────────────────────────┘
```

**Implementation Example:**

```python
# oiduna_core/engine/engine_process.py
from multiprocessing import Process, Queue
from oiduna_core.engine.loop_engine import LoopEngine

def run_engine_process(command_queue: Queue, state_queue: Queue):
    """Run loop engine in dedicated process."""
    engine = LoopEngine(...)

    while True:
        # Non-blocking command check
        while not command_queue.empty():
            cmd = command_queue.get_nowait()

            if cmd['type'] == 'load_session':
                engine.load_session(cmd['data'])
            elif cmd['type'] == 'start':
                engine.start()
            elif cmd['type'] == 'stop':
                engine.stop()

        # Tick loop engine (dedicated GIL)
        engine.tick()

        # Send state updates (non-blocking)
        if not state_queue.full():
            state_queue.put({
                'step': engine.position.step,
                'playing': engine.is_playing,
            })
```

```python
# oiduna_core/api/routes/playback.py
from multiprocessing import Process, Queue

# Global process and queues
_command_queue = Queue(maxsize=100)
_state_queue = Queue(maxsize=10)
_engine_process = None

def init_engine():
    global _engine_process
    _engine_process = Process(
        target=run_engine_process,
        args=(_command_queue, _state_queue)
    )
    _engine_process.start()

@router.post("/pattern")
async def submit_pattern(session: dict):
    # Parse in API process (can be slow)
    compiled = CompiledSession.from_dict(session)

    # Send to engine process (non-blocking)
    _command_queue.put({
        'type': 'load_session',
        'data': compiled
    })

    return {"success": True}
```

**Pros:**
- ✅ Complete GIL isolation
- ✅ Loop engine never blocked
- ✅ Can do heavy processing in API
- ✅ Same design as original MARS

**Cons:**
- ❌ More complex architecture
- ❌ IPC overhead (minimal with Queue)
- ❌ Harder to debug

**When to Implement:**
- Phase 3: If real-time parameter updates are needed
- When API processing becomes heavy
- If audio glitches are observed

---

### Strategy 3: AsyncIO Optimization (Not Recommended)

**Approach:**
- Use `asyncio.to_thread()` or `loop.run_in_executor()`
- Offload heavy work to thread pool

```python
@router.post("/pattern")
async def submit_pattern(session: dict):
    loop = asyncio.get_event_loop()

    # Run in thread pool
    compiled = await loop.run_in_executor(
        None,
        CompiledSession.from_dict,
        session
    )
```

**Why This Doesn't Work:**
- ❌ Thread pool still shares the GIL
- ❌ Heavy operations block other threads
- ❌ No real concurrency for CPU-bound work
- ❌ Only helps with I/O-bound operations

**Verdict:** Not suitable for this use case.

---

## Implementation Roadmap

### Phase 1 (Current) ✅
- **Status:** Complete
- **Architecture:** Single process
- **Processing:** IR reception only (~10ms)
- **Risk:** None (no heavy operations)

### Phase 2 (MARS Distribution)
- **Timeline:** Next 3-4 weeks
- **Strategy:** Keep heavy processing external (Strategy 1)
- **Changes:** None to Oiduna Core
- **Implementation:**
  1. MARS Distribution implements DSL compiler
  2. Sends compiled IR to Oiduna via HTTP POST
  3. Monitor for any performance issues

### Phase 3 (Advanced Features)
- **Timeline:** 4-5 weeks after Phase 2
- **Trigger:** If audio glitches observed OR real-time features needed
- **Strategy:** Multi-process loop engine (Strategy 2)
- **Implementation:**
  1. Create `oiduna_core/engine/engine_process.py`
  2. Add `multiprocessing.Queue` IPC
  3. Update API routes to use queues
  4. Benchmark before/after

---

## Performance Monitoring

### Metrics to Track

```python
# Add to loop_engine.py
import time

class LoopEngine:
    def tick(self):
        start = time.perf_counter()

        # ... existing tick logic ...

        elapsed = time.perf_counter() - start

        # Log if tick takes too long
        if elapsed > 0.010:  # 10ms threshold
            logger.warning(
                f"Slow tick: {elapsed*1000:.2f}ms at step {self.position.step}"
            )
```

### Health Check Endpoint

```python
@router.get("/metrics")
async def get_metrics():
    return {
        "average_tick_time_ms": engine.get_avg_tick_time(),
        "max_tick_time_ms": engine.get_max_tick_time(),
        "dropped_steps": engine.dropped_step_count,
    }
```

---

## Decision Matrix

| Use Case                        | Recommended Strategy | Timing  |
|---------------------------------|----------------------|---------|
| IR reception only               | Current (single)     | Phase 1 |
| DSL compilation external        | Strategy 1 (external)| Phase 2 |
| Real-time param updates (light) | Current (single)     | Phase 2 |
| Real-time param updates (heavy) | Strategy 2 (multi)   | Phase 3 |
| Audio glitches observed         | Strategy 2 (multi)   | ASAP    |

---

## References

### Original MARS Implementation
- `packages/mars_loop/engine/loop_engine.py` (ZeroMQ-based)
- `packages/mars_api/main.py` (Separate API process)
- ZeroMQ IPC design: ~0.1ms latency, non-blocking

### Python GIL Documentation
- [PEP 703 - Making the Global Interpreter Lock Optional](https://peps.python.org/pep-0703/)
- [Python Threading Guide](https://docs.python.org/3/library/threading.html)

### Benchmarking Tools
- `cProfile` for profiling
- `py-spy` for sampling profiler
- `perf` for system-level analysis

---

## Conclusion

**Current Status (Phase 1):**
- ✅ No GIL issues (lightweight IR processing only)
- ✅ Single-process architecture is appropriate

**Phase 2 Strategy:**
- ✅ Keep DSL compilation in Distribution (Strategy 1)
- ✅ Monitor performance metrics
- ⚠️ Be ready to implement Strategy 2 if needed

**Phase 3 Decision Point:**
- If audio glitches observed → Implement Strategy 2
- If no issues → Continue with current architecture
- Measure before optimizing

**Key Principle:**
> "Premature optimization is the root of all evil" - Donald Knuth

We'll implement multi-process only when measurements show it's necessary.
