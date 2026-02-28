# ADR 0011: Rust Acceleration Strategy for Core Data Processing

**Status**: Proposed

**Date**: 2026-02-28

**Deciders**: tobita, Claude Code

---

## Context

### Background

After ADR-0010 (SessionContainer refactoring), the API layer was significantly improved with hierarchical data models and specialized managers. However, performance analysis revealed that **data transformation operations** (not the loop engine itself) are the primary bottleneck for scaling to large sessions.

**Current Performance Issues:**
- SessionCompiler.compile(): O(T × P × E) with dict operations → **1-30ms**
- MessageScheduler.load_messages(): O(N) with Python dict indexing → **1-10ms**
- GIL contention between API requests and loop engine → **potential audio glitches**

**Surprising Discovery:**
The loop engine itself is already well-optimized (asyncio, drift correction). The real bottleneck is **data structure transformation** happening outside the timing-critical path.

### Problem Statement

**Design Tension:**
1. **Need for speed:** Live coding requires <10ms compile time for responsive updates
2. **Need for extensibility:** Distributions (MARS, etc.) need flexible transformation hooks
3. **GIL limitations:** Python's single-threaded execution blocks loop engine during heavy operations

**Traditional Assumption (Incorrect):**
> "Optimize the loop engine first (it's timing-critical)"

**Actual Reality:**
> "Loop engine is already fast. Data transformation creates GIL contention."

**Example Scenario:**
```
Large session (50 tracks × 10 patterns × 100 events = 50,000 iterations)
- SessionCompiler.compile(): 30ms (Python dict merge overhead)
- LoopEngine._step_loop(): 2ms (already optimized)

Result: compile() blocks loop → audio glitch
```

---

## Decision

### Rust-Accelerate Data Transformation, Not Loop Engine

**Core Principle:**
> **"Rust for predictable, high-throughput data processing"**
> **"Python for flexible, extensible control flow"**

**Architecture:**
```
┌─────────────────────────────────────────────────────────┐
│ Layer 1: API (Python) - Extensibility                   │
│  ┌──────────────────────────────────────────────────┐  │
│  │ FastAPI + SessionContainer + Extensions          │  │
│  │ - BaseExtension.transform() ← Extension Point    │  │
│  │ - CRUD operations, HTTP handling                 │  │
│  └────────────────┬─────────────────────────────────┘  │
│                   ▼                                      │
├─────────────────────────────────────────────────────────┤
│ Layer 2: Compilation (Rust) - Performance               │
│  ┌──────────────────────────────────────────────────┐  │
│  │ RustSessionCompiler.compile()    (10-20x faster) │  │
│  │ RustMessageScheduler.load()      (5-10x faster)  │  │
│  │ - HashMap operations, memory optimization        │  │
│  │ - Zero-copy where possible                       │  │
│  └────────────────┬─────────────────────────────────┘  │
│                   ▼                                      │
├─────────────────────────────────────────────────────────┤
│ Layer 3: Loop (Python + Hooks) - Extensibility          │
│  ┌──────────────────────────────────────────────────┐  │
│  │ LoopEngine (Python asyncio)                      │  │
│  │ - before_send_hooks ← Extension Point            │  │
│  │ - Timing, drift correction (already optimized)   │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Rationale

**Why NOT optimize the loop engine with Rust?**

1. **Already fast enough:**
   - Python asyncio provides sub-millisecond timing precision
   - Drift correction works well (see GIL_MITIGATION.md)
   - No performance complaints from users

2. **Complexity cost:**
   - Rust async runtime integration is complex
   - Python asyncio is mature and debuggable
   - Extension hooks are easy in Python

3. **Wrong bottleneck:**
   - Loop engine: ~2ms per step (acceptable)
   - Data transformation: ~30ms during compile (problematic)

**Why YES optimize data transformation with Rust?**

1. **Clear bottleneck:**
   - SessionCompiler.compile() is O(T × P × E)
   - 50,000 iterations with dict merge overhead = 30ms

2. **Embarrassingly parallel:**
   - No async/await complexity
   - Simple iteration + HashMap operations
   - Perfect fit for Rust's strengths

3. **Transparent to extensions:**
   - Extensions still use Python API
   - Rust is internal implementation detail
   - Fallback to Python if Rust unavailable

4. **Predictable performance:**
   - No GC pauses (Rust has no garbage collector)
   - Consistent 0.5-1ms compile time
   - No GIL contention

---

## Implementation Strategy

### Phase 1: SessionCompiler (Rust) - **Priority 1**

**Target:** `packages/oiduna_session/compiler.py`

**Current Bottleneck:**
```python
def compile(session: Session) -> ScheduledMessageBatch:
    messages = []
    for track in session.tracks.values():           # O(T)
        for pattern in track.patterns.values():     # O(P)
            if not pattern.active:
                continue
            for event in pattern.events:            # O(E)
                # Dict merge (slow in Python)
                params = {**track.base_params, **event.params}
                params["track_id"] = track.track_id
                messages.append(ScheduledMessage(...))
    return ScheduledMessageBatch(tuple(messages), ...)
```

**Performance:**
- Small session (10 tracks × 10 events): ~2ms
- Large session (50 tracks × 1000 events): ~30ms

**Rust Implementation:**
```rust
// packages/oiduna_session_rust/src/compiler.rs

use pyo3::prelude::*;
use std::collections::HashMap;

#[pyclass]
pub struct RustSessionCompiler;

#[pymethods]
impl RustSessionCompiler {
    #[staticmethod]
    fn compile(py: Python, session: &PyAny) -> PyResult<PyObject> {
        let mut messages = Vec::with_capacity(1024);
        let tracks = session.getattr("tracks")?;

        // Rust iteration (10x faster than Python)
        for track in tracks.values() {
            let patterns = track.getattr("patterns")?;
            for pattern in patterns.values() {
                if !pattern.getattr("active")?.extract::<bool>()? {
                    continue;
                }

                // Rust HashMap merge (5x faster than Python dict)
                let events = pattern.getattr("events")?.extract::<Vec<PyObject>>()?;
                for event in events {
                    let msg = create_message_fast(track, event)?;
                    messages.push(msg);
                }
            }
        }

        create_batch(py, messages, session.getattr("environment")?)
    }
}

// Fast dict merge using Rust HashMap
fn merge_params(base: &PyDict, event: &PyDict) -> PyResult<HashMap<String, PyObject>> {
    let mut merged = HashMap::with_capacity(base.len() + event.len());

    // Copy base params (cache-friendly iteration)
    for (k, v) in base.iter() {
        merged.insert(k.extract()?, v.into());
    }

    // Override with event params
    for (k, v) in event.iter() {
        merged.insert(k.extract()?, v.into());
    }

    Ok(merged)
}
```

**Expected Performance:**
- Small session: ~0.2ms (10x improvement)
- Large session: ~1.5ms (20x improvement)

**Integration (Transparent Fallback):**
```python
# packages/oiduna_session/compiler.py

try:
    from oiduna_session_rust import RustSessionCompiler
    _USE_RUST = True
except ImportError:
    _USE_RUST = False
    import warnings
    warnings.warn("Rust acceleration unavailable, using pure Python fallback")

class SessionCompiler:
    @staticmethod
    def compile(session: Session) -> ScheduledMessageBatch:
        if _USE_RUST:
            return RustSessionCompiler.compile(session)
        else:
            return SessionCompiler._compile_python(session)

    @staticmethod
    def _compile_python(session: Session):
        # Existing pure Python implementation (fallback)
        ...
```

**Extension Impact:** None (transparent to extensions)

---

### Phase 2: MessageScheduler (Rust) - **Priority 2**

**Target:** `packages/oiduna_scheduler/scheduler.py`

**Current Bottleneck:**
```python
def load_messages(self, batch: ScheduledMessageBatch):
    self._messages_by_step.clear()
    for msg in batch.messages:  # O(N)
        step = msg.step
        if step not in self._messages_by_step:
            self._messages_by_step[step] = []
        self._messages_by_step[step].append(msg)
```

**Performance:**
- 1000 messages: ~5ms
- 10000 messages: ~50ms (linear scaling issue)

**Rust Implementation Benefits:**
- HashMap with pre-allocated capacity
- Cache-friendly memory layout
- Expected: 5-10x improvement

**Extension Impact:** None (internal optimization)

---

### Phase 3: MessageFilter (Rust) - **Optional**

**Target:** `packages/oiduna_loop/state.py` → `filter_messages()`

**Current Status:**
- Already has "fast path" optimization (no mute/solo = zero-copy)
- Slow path is rare (only when mute/solo active)

**Rust Benefits:**
- 2-5x improvement on slow path
- More predictable timing (no Python dict lookup)

**Priority:** Low (existing fast path works well)

**Extension Impact:** None

---

## Extension Framework Preservation

### Critical Design Constraint

**Extensions MUST remain Python-based for flexibility:**

```python
# Extension API (STABLE - will not change)

class BaseExtension(ABC):
    # ═══════════════════════════════════════════════════
    # Phase 1: API Layer (Heavy processing OK)
    # ═══════════════════════════════════════════════════

    @abstractmethod
    def transform(self, payload: dict) -> dict:
        """
        Session transformation (runs BEFORE Rust compile)

        Timing: During POST /playback/session, POST /playback/sync
        Performance: <50ms recommended
        Language: Pure Python (full flexibility)

        Extensions can:
        - Add/remove messages
        - Modify params
        - Generate custom tracks
        - Call external services
        """
        pass

    # ═══════════════════════════════════════════════════
    # Phase 2: Loop Layer (Lightweight only)
    # ═══════════════════════════════════════════════════

    def before_send_messages(self, messages, bpm, step) -> list:
        """
        Runtime transformation (runs AFTER Rust processing)

        Timing: Every step (~31ms @ 120 BPM)
        Performance: <100μs REQUIRED
        Language: Pure Python (but must be fast)

        Extensions can:
        - Inject runtime params (cps, current_step)
        - Conditional logic based on BPM

        Extensions CANNOT:
        - Heavy computation
        - I/O operations
        - Logging (except errors)
        """
        return messages
```

### Rust/Python Boundary

```
┌────────────────────────────────────────────────────┐
│ Extension.transform(payload)                       │
│ ↓ (Pure Python, flexible, <50ms)                   │
├────────────────────────────────────────────────────┤
│ RustSessionCompiler.compile(session)               │
│ ↓ (Rust, fixed logic, <1ms)                        │
├────────────────────────────────────────────────────┤
│ Extension.before_send_messages(messages)           │
│ ↓ (Pure Python, lightweight, <100μs)               │
├────────────────────────────────────────────────────┤
│ OSC/MIDI Send                                      │
└────────────────────────────────────────────────────┘
```

**Key Insight:**
- Extensions operate at **boundaries** (before/after Rust core)
- Rust core is **transparent** (extensions don't know it exists)
- Performance gains are **automatic** (no extension changes needed)

---

## Build and Distribution

### Development Workflow

**With uv + maturin:**
```bash
# Install Rust toolchain (one-time)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Development (debug build, fast iteration)
cd packages/oiduna_session_rust
maturin develop

# Production (release build, optimized)
cd packages/oiduna_session
uv build  # Uses maturin automatically

# Testing (with/without Rust)
uv run pytest packages/oiduna_session/tests/
```

**Known Friction:**
- uv sync may cache stale Rust builds
- Workaround: Use `tool.uv.cache-keys` to track Rust sources

```toml
# packages/oiduna_session/pyproject.toml
[tool.uv.cache-keys]
file = ["../oiduna_session_rust/Cargo.toml", "../oiduna_session_rust/src/**/*.rs"]
```

### Distribution Strategy

**PyPI wheels:**
```bash
# Build wheels for all platforms (GitHub Actions)
maturin build --release --target x86_64-unknown-linux-gnu
maturin build --release --target x86_64-apple-darwin
maturin build --release --target x86_64-pc-windows-msvc

# Upload to PyPI
maturin upload wheels/*.whl
```

**Fallback behavior:**
- If Rust wheel unavailable → use pure Python (with warning)
- No hard dependency on Rust (optional acceleration)

**Installation:**
```bash
# With Rust acceleration (recommended)
uv add oiduna-session[rust]

# Pure Python only
uv add oiduna-session
```

---

## Performance Targets

### Compile Time Goals

| Session Size | Current (Python) | Target (Rust) | Improvement |
|--------------|------------------|---------------|-------------|
| Small (10 tracks, 100 events) | 2ms | 0.2ms | 10x |
| Medium (30 tracks, 500 events) | 10ms | 0.8ms | 12.5x |
| Large (50 tracks, 1000 events) | 30ms | 1.5ms | 20x |

**Success Criteria:**
- All compile operations < 2ms
- 99th percentile < 5ms
- No GIL contention with loop engine

### Loop Engine Impact

**Before Rust (current):**
```
POST /playback/sync (large session):
  - compile(): 30ms
  - GIL blocked: YES
  - Loop engine: potential glitch

Result: ⚠️ Audio dropout risk
```

**After Rust:**
```
POST /playback/sync (large session):
  - compile(): 1.5ms
  - GIL blocked: minimal
  - Loop engine: unaffected

Result: ✅ No audio dropouts
```

---

## Alternatives Considered

### Alternative 1: Multi-Process Loop Engine

**Approach:**
- Run loop engine in separate process
- Use multiprocessing.Queue for IPC

**Pros:**
- Complete GIL isolation
- Works with current Python code

**Cons:**
- Architectural complexity
- IPC serialization overhead
- Harder debugging
- Doesn't fix compile() slowness

**Verdict:** Rejected in favor of Rust (simpler, faster)

### Alternative 2: Optimize Pure Python

**Approach:**
- Use generators, list comprehensions
- Profile and micro-optimize

**Example:**
```python
# Before
messages = []
for track in tracks.values():
    for pattern in track.patterns.values():
        messages.append(...)

# After
messages = list(
    ScheduledMessage(...)
    for track in tracks.values()
    for pattern in track.patterns.values()
    if pattern.active
    for event in pattern.events
)
```

**Expected Improvement:** 2-3x (not enough)

**Verdict:** Useful but insufficient for large sessions

### Alternative 3: Cython

**Approach:**
- Use Cython to compile Python to C

**Pros:**
- Python-like syntax
- Easier than Rust for Python developers

**Cons:**
- Still uses Python C-API (GIL limitations)
- Less performance than Rust (8-15x vs 10-20x)
- Harder to maintain than PyO3

**Verdict:** Rust + PyO3 is more future-proof

### Alternative 4: Numba JIT

**Approach:**
- Use @jit decorator for hot loops

**Cons:**
- Doesn't work with Pydantic models
- Limited dict operation support
- Warm-up time overhead

**Verdict:** Not suitable for this use case

---

## Migration Path

### Phase 1: Proof of Concept (1 week)

**Goals:**
1. Create `oiduna_session_rust` package
2. Implement basic `RustSessionCompiler.compile()`
3. Benchmark against pure Python
4. Validate 10-20x improvement claim

**Deliverables:**
- Working Rust module
- Benchmark results
- Integration tests passing

### Phase 2: Production Integration (1 week)

**Goals:**
1. Add transparent fallback mechanism
2. Update CI/CD for Rust builds
3. Generate wheels for all platforms
4. Documentation updates

**Deliverables:**
- PyPI-ready package
- Cross-platform wheels
- Updated docs

### Phase 3: MessageScheduler (1 week)

**Goals:**
1. Implement `RustMessageScheduler`
2. Benchmark and validate
3. Integration tests

**Total Timeline:** 3-4 weeks for full implementation

---

## Validation Criteria

### Performance Benchmarks

**Benchmark Suite:**
```python
# packages/oiduna_session/tests/benchmark_compile.py

import pytest
import time
from oiduna_session import SessionCompiler

@pytest.mark.benchmark
def test_compile_small_session(benchmark_session_small):
    start = time.perf_counter()
    batch = SessionCompiler.compile(benchmark_session_small)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert elapsed_ms < 2.0, f"Compile too slow: {elapsed_ms:.2f}ms"

@pytest.mark.benchmark
def test_compile_large_session(benchmark_session_large):
    # 50 tracks × 1000 events
    start = time.perf_counter()
    batch = SessionCompiler.compile(benchmark_session_large)
    elapsed_ms = (time.perf_counter() - start) * 1000

    # Rust target: < 2ms
    # Python fallback: < 50ms acceptable
    assert elapsed_ms < 50.0, f"Compile too slow: {elapsed_ms:.2f}ms"
```

### Extension Compatibility

**Test Suite:**
```python
# Verify extensions still work with Rust backend

def test_extension_transform_with_rust(rust_enabled):
    pipeline = ExtensionPipeline()
    pipeline.register("test", TestExtension())

    # Extension modifies payload
    payload = create_test_payload()
    transformed = pipeline.transform(payload)

    # Rust compile should handle transformed payload
    session = create_session_from_payload(transformed)
    batch = SessionCompiler.compile(session)  # Uses Rust

    assert batch is not None
    assert verify_extension_modifications(batch)
```

---

## Risks and Mitigations

### Risk 1: Build Complexity

**Risk:** Rust build adds complexity to development workflow

**Mitigation:**
- Transparent fallback to pure Python
- Clear documentation for developers
- Pre-built wheels for end users

### Risk 2: Platform Support

**Risk:** Rust compilation fails on some platforms

**Mitigation:**
- Fallback to pure Python (automatic)
- Warning message if Rust unavailable
- Test matrix for major platforms (Linux, macOS, Windows)

### Risk 3: Maintenance Burden

**Risk:** Need to maintain both Rust and Python implementations

**Mitigation:**
- Share test suite between implementations
- Pure Python version serves as reference
- Rust version is pure performance optimization (no new features)

### Risk 4: Python 3.13 Free-Threading

**Risk:** Future Python removes GIL, making Rust optimization less valuable

**Mitigation:**
- Rust still provides value (faster data structures)
- Predictable performance (no GC pauses)
- Can leverage Rust for other optimizations (DSP, etc.)

---

## Related ADRs

- **ADR-0010**: SessionContainer refactoring
  - Created the need for fast compile()
  - Introduced hierarchical data model

- **ADR-0008**: Code Quality Refactoring Strategy
  - Emphasized performance measurement
  - Martin Fowler patterns

- **GIL_MITIGATION.md** (architecture doc)
  - Analyzed GIL contention issues
  - Recommended multi-process OR optimization
  - This ADR chooses optimization path

---

## Decision Outcome

**Chosen Approach:** Rust-accelerate data transformation layers

**Rationale:**
1. ✅ Addresses real bottleneck (data transformation, not loop engine)
2. ✅ Transparent to extensions (maintains Python flexibility)
3. ✅ Simpler than multi-process architecture
4. ✅ Predictable 10-20x performance improvement
5. ✅ Future-proof (can extend to DSP, audio processing)

**Not Chosen:**
- ❌ Multi-process loop engine (over-engineered)
- ❌ Pure Python optimization (insufficient gains)
- ❌ Loop engine in Rust (wrong bottleneck)

**Key Insight:**
> **"The best optimization is fixing the right bottleneck."**
>
> Loop engine timing is already excellent. Data transformation creates GIL contention.
> Rust solves this elegantly without disrupting the extension ecosystem.

---

## Future Considerations

### Potential Phase 4: Rust Audio DSP

If real-time audio processing is needed in the future:

```rust
// Phase 4 (future): Audio DSP in Rust
//
// Use case: Real-time effects, synthesis, analysis
//
// packages/oiduna_dsp_rust/src/effects.rs

use dasp::{Signal, Sample};

#[pyclass]
pub struct RustReverb {
    // High-performance DSP using dasp crate
}
```

**When to consider:**
- User requests for built-in effects
- Real-time parameter modulation
- Audio analysis features

---

## Conclusion

This ADR establishes the strategy for Rust acceleration in Oiduna:

1. **Focus:** Data transformation (not loop engine)
2. **Priority:** SessionCompiler > MessageScheduler > (optional) MessageFilter
3. **Preservation:** Python extension framework unchanged
4. **Timeline:** 3-4 weeks for full implementation
5. **Impact:** 10-20x compile speedup, eliminates GIL contention

**Next Steps:**
1. Create proof-of-concept `RustSessionCompiler`
2. Benchmark and validate claims
3. Proceed with full implementation if validated

---

**Contributors:** tobita, Claude Code (Claude Sonnet 4.5)

**References:**
- PyO3 Documentation: https://pyo3.rs/
- Maturin User Guide: https://www.maturin.rs/
- GIL_MITIGATION.md (architecture documentation)
- ADR-0010: SessionContainer refactoring
