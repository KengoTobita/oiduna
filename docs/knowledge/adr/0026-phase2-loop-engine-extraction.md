# ADR-0026: Phase 2 Code Quality - LoopEngine Service Extraction

**Status:** Accepted
**Date:** 2026-03-13
**Deciders:** Kengo Tobita, Claude Sonnet 4.5
**Related:** ADR-0024 (Phase 1), ADR-0003 (Python Timing Engine), ADR-0008 (Code Quality Strategy)

---

## Context

Following Phase 1 code quality improvements (ADR-0024), Phase 2 continues with infrastructure layer refactoring. The `LoopEngine` class had grown to 1034 lines with multiple responsibilities, violating the Single Responsibility Principle.

### Identified Issues

#### 1. God Class Anti-Pattern

`LoopEngine` handled too many responsibilities:

```python
class LoopEngine:
    """
    Main loop engine - handles:
    - Step sequencing (16th notes)
    - MIDI clock generation (24 PPQ)
    - OSC/MIDI output
    - IPC communication
    - Drift correction ← Responsibility 1
    - Connection monitoring ← Responsibility 2
    - Heartbeat messages ← Responsibility 3
    """

    # 1034 lines total
    # 230+ lines of drift/connection/heartbeat logic
```

**Problems:**
- **SRP violation:** Single class with 3+ distinct responsibilities
- **Testing difficulty:** Drift logic tested through LoopEngine integration
- **Code duplication:** Similar drift logic in `ClockGenerator` (80 lines)
- **Maintainability:** Hard to modify drift algorithm without touching LoopEngine

#### 2. Duplicated Drift Correction Logic

Drift correction appeared in 2 places:

**LoopEngine (150 lines):**
```python
# Step loop drift correction
self._step_anchor_time: float | None = None
self._step_count: int = 0
self._suppress_next_drift_reset: bool = False
self._drift_stats: dict[str, float | int] = {...}

async def _step_loop(self):
    # 70 lines of drift detection/reset logic

async def _handle_drift_reset(self, drift_ms, current_time):
    # 40 lines of drift reset handling
```

**ClockGenerator (80 lines):**
```python
# MIDI clock drift correction (nearly identical logic)
self._clock_anchor_time: float | None = None
self._pulse_count: int = 0
self._suppress_next_drift_reset: bool = False
self._drift_stats: dict[str, float | int] = {...}

def _handle_drift_reset(self, drift_ms, current_time):
    # 40 lines of drift reset handling (duplicated)
```

**Impact:**
- 230 lines of duplicated/similar logic
- Algorithm changes require editing 2 classes
- Testing requires 2 separate test suites

#### 3. Tight Coupling

Heartbeat and connection monitoring tightly coupled to LoopEngine:

```python
async def _heartbeat_loop(self):
    """Tightly coupled - can't test in isolation."""
    while self._running:
        await self._check_connections()  # Connection logic embedded
        await self.send_heartbeat()       # Heartbeat logic embedded
        await asyncio.sleep(self.HEARTBEAT_INTERVAL)
```

---

## Decision

Apply **Extract Class** pattern (Refactoring, p.182) to separate responsibilities into focused services.

### Solution: Service Extraction

Extract 3 service classes following Single Responsibility Principle:

#### Service 1: DriftCorrector (~150 lines)

**Responsibility:** Clock drift detection and correction

```python
class DriftCorrector:
    """
    Manages clock drift detection and correction.

    Uses anchor-based timing to track expected vs actual execution times.
    Automatically resets anchor when drift exceeds threshold.
    """

    def __init__(
        self,
        reset_threshold_ms: float = 50.0,
        warning_threshold_ms: float = 20.0,
        notifier: DriftNotifier | None = None,
    ):
        self._anchor_time: float | None = None
        self._count: int = 0
        self._suppress_next_reset = False
        self._stats: dict[str, float | int] = {...}

    async def check_drift(
        self,
        interval_duration: float,
        context_name: str = "clock",
    ) -> tuple[bool, float]:
        """Check for drift and handle if necessary."""
        # Drift detection and reset logic

    def advance(self) -> None:
        """Advance the counter after successful interval."""

    def reset(self) -> None:
        """Reset drift correction state."""
```

**Benefits:**
- Single responsibility: Only drift management
- Reusable: Used by both LoopEngine and ClockGenerator
- Testable: 11 isolated unit tests

#### Service 2: ConnectionMonitor (~50 lines)

**Responsibility:** Connection status tracking

```python
class ConnectionMonitor:
    """
    Monitors connection status for output devices.

    Tracks MIDI and OSC connection status and sends notifications
    when connections are lost.
    """

    async def check_connections(
        self,
        connections: dict[str, ConnectionCheckable],
    ) -> None:
        """Check connection status and notify on changes."""
        # Status tracking and notification logic

    def get_status(self) -> dict[str, bool]:
        """Get current connection status."""
```

**Benefits:**
- Single responsibility: Only connection monitoring
- Protocol-based: `ConnectionCheckable` protocol for flexibility
- Testable: 9 isolated unit tests

#### Service 3: HeartbeatService (~30 lines)

**Responsibility:** Periodic health monitoring

```python
class HeartbeatService:
    """
    Manages periodic heartbeat messages and health monitoring.

    Sends periodic heartbeat messages to indicate engine is alive.
    Supports registering custom tasks to run periodically.
    """

    def register_task(self, task: Callable[[], Awaitable[None]]) -> None:
        """Register a custom task to run with each heartbeat."""

    async def run_loop(self, running_flag: Callable[[], bool]) -> None:
        """Run the heartbeat loop."""
        # Heartbeat and task execution logic
```

**Benefits:**
- Single responsibility: Only heartbeat management
- Extensible: Custom tasks can be registered
- Testable: 9 isolated unit tests

### Protocol-Based Dependency Injection

Services use protocols for loose coupling:

```python
# DriftCorrector notification protocol
class DriftNotifier(Protocol):
    async def send_error(self, error_code: str, message: str) -> None:
        ...

# ConnectionMonitor protocols
class ConnectionCheckable(Protocol):
    @property
    def is_connected(self) -> bool:
        ...

class ConnectionStatusNotifier(Protocol):
    async def send_error(self, error_code: str, message: str) -> None:
        ...

# HeartbeatService protocol
class HeartbeatPublisher(Protocol):
    async def send(self, message_type: str, payload: dict) -> None:
        ...
```

---

## Implementation

### Refactored LoopEngine

**Before (1034 lines):**
```python
class LoopEngine:
    def __init__(self, ...):
        # Drift correction state
        self._step_anchor_time: float | None = None
        self._step_count: int = 0
        self._suppress_next_drift_reset: bool = False
        self._drift_stats: dict[str, float | int] = {...}

        # Connection status tracking
        self._connection_status: dict[str, bool] = {...}

    async def _step_loop(self):
        # 70 lines of drift detection logic
        ...

    async def _handle_drift_reset(self, drift_ms, current_time):
        # 40 lines of drift reset logic
        ...

    async def _check_connections(self):
        # 25 lines of connection monitoring
        ...

    async def _heartbeat_loop(self):
        # 20 lines of heartbeat logic
        ...
```

**After (944 lines, 8.7% reduction):**
```python
class LoopEngine:
    def __init__(self, ...):
        # Phase 2: Extracted services
        self._drift_corrector = DriftCorrector(
            reset_threshold_ms=50.0,
            warning_threshold_ms=20.0,
            notifier=self._state_producer,
        )
        self._connection_monitor = ConnectionMonitor(
            notifier=self._state_producer,
        )
        self._heartbeat_service = HeartbeatService(
            publisher=self._state_producer,
            interval=5.0,
        )

    async def _step_loop(self):
        # Delegated to DriftCorrector
        should_reset, drift_ms = await self._drift_corrector.check_drift(
            step_duration,
            "Step loop",
        )
        if should_reset:
            await asyncio.sleep(step_duration)
            continue

        await self._execute_current_step()
        await self._wait_for_next_step()

    async def _heartbeat_loop(self):
        # Delegated to services
        async def check_connections_task():
            await self._connection_monitor.check_connections({
                "midi": self._midi,
                "osc": self._osc,
            })

        self._heartbeat_service.register_task(check_connections_task)
        await self._heartbeat_service.run_loop(lambda: self._running)
```

### Refactored ClockGenerator

**Before (~300 lines):**
```python
class ClockGenerator:
    def __init__(self, midi: MidiOutput):
        # Duplicated drift correction state
        self._clock_anchor_time: float | None = None
        self._pulse_count: int = 0
        self._suppress_next_drift_reset: bool = False
        self._drift_stats: dict[str, float | int] = {...}

    async def run_clock_loop(self, ...):
        # 80 lines of drift correction logic (duplicated)
        ...
```

**After (~245 lines, 18% reduction):**
```python
class ClockGenerator:
    def __init__(self, midi: MidiOutput):
        # Phase 2: Uses DriftCorrector service
        self._drift_corrector = DriftCorrector(
            reset_threshold_ms=30.0,
            warning_threshold_ms=15.0,
            notifier=None,  # Clock drift is silent
        )

    async def run_clock_loop(self, ...):
        # Delegated to DriftCorrector
        should_reset, drift_ms = await self._drift_corrector.check_drift(
            pulse_duration,
            "MIDI clock",
        )
        if should_reset:
            await asyncio.sleep(pulse_duration)
            continue

        self._midi.send_clock()
        self._drift_corrector.advance()
```

---

## Consequences

### Positive

✅ **Single Responsibility Principle:** Each service has one clear purpose
✅ **Code reduction:** 145 lines removed (net: -90 LoopEngine, -55 ClockGenerator)
✅ **Testability:** 29 new isolated service tests (11 + 9 + 9)
✅ **Reusability:** DriftCorrector shared by LoopEngine and ClockGenerator
✅ **Maintainability:** Drift algorithm changes only touch DriftCorrector
✅ **Extensibility:** Protocol-based design allows easy mocking/replacement

### Code Metrics

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| LoopEngine lines | 1034 | 944 | **-8.7%** |
| ClockGenerator lines | ~300 | ~245 | **-18%** |
| New service files | 0 | 3 | +230 lines |
| Net change | - | - | **-145 lines** |
| Test coverage | 370 tests | 399 tests | +29 tests |

### Test Results

```
378 passed, 29 skipped, 1 warning in 1.76s
```

- **100% pass rate maintained**
- 29 tests skipped (obsolete internal drift tests, now in service tests)
- 29 new service tests added
- All existing integration tests pass

### Trade-offs

⚠️ **More files:** 3 new service files + tests
   - **Mitigation:** Services package with clear __init__.py exports
   - **Benefit:** Better code organization

⚠️ **Obsolete tests:** 29 tests accessing internal state marked as skipped
   - **Reason:** Tests accessed private drift state now in services
   - **Mitigation:** Comprehensive service tests replace them
   - **Future:** Remove skipped tests in Phase 3

---

## Design Patterns Applied

1. **Extract Class** (Refactoring, p.182)
   - Extracted 3 service classes from LoopEngine
   - Each service has single, focused responsibility

2. **Single Responsibility Principle** (SOLID)
   - DriftCorrector: Only drift management
   - ConnectionMonitor: Only connection tracking
   - HeartbeatService: Only periodic monitoring

3. **Protocol-Based Dependency Injection**
   - `DriftNotifier`, `ConnectionCheckable`, `HeartbeatPublisher` protocols
   - Enables loose coupling and testability

4. **Extract Function** (Refactoring, p.106)
   - Drift checking, connection monitoring, heartbeat logic extracted

---

## Files Modified

**Source files:**
- `src/oiduna/infrastructure/execution/loop_engine.py` (1034 → 944 lines)
- `src/oiduna/infrastructure/execution/clock_generator.py` (~300 → ~245 lines)

**New service files:**
- `src/oiduna/infrastructure/execution/services/drift_corrector.py` (~150 lines)
- `src/oiduna/infrastructure/execution/services/connection_monitor.py` (~50 lines)
- `src/oiduna/infrastructure/execution/services/heartbeat_service.py` (~30 lines)
- `src/oiduna/infrastructure/execution/services/__init__.py`

**Test files:**
- `tests/infrastructure/execution/test_connection_status.py` (updated for services)
- `tests/infrastructure/execution/test_drift_reset.py` (21 obsolete tests removed, 10 tests retained)
- `tests/infrastructure/execution/test_stability.py` (8 stability tests migrated to Phase 2 architecture)
- `tests/infrastructure/execution/services/test_drift_corrector.py` (11 tests)
- `tests/infrastructure/execution/services/test_connection_monitor.py` (9 tests)
- `tests/infrastructure/execution/services/test_heartbeat_service.py` (9 tests)

---

## Post-Implementation Updates

### Obsolete Tests Cleanup (2026-03-13)

**Removed 21 obsolete tests from test_drift_reset.py:**
- Tests accessing internal state (`_step_anchor_time`, `_step_count`, `_drift_stats`)
- Tests calling private methods (`_handle_drift_reset()`)
- Tests replaced by DriftCorrector service tests

**Retained 10 valid tests:**
- TestDriftResetConstants (4 tests) - configuration constants
- TestLoopEngineDriftStats (2 tests) - public API `get_drift_stats()`
- TestClockGeneratorDriftReset (1 test) - public API
- TestDriftCalculation (3 tests) - pure calculation logic

**Result:** 375 passed, 0 skipped (previously 378 passed, 29 skipped)

### Stability Tests Migration (2026-03-13)

**Migrated 8 stability tests to Phase 2 architecture:**

All tests in `test_stability.py` updated to use DriftCorrector service:
1. LoopEngine API: `commands` → `command_consumer`, `publisher` → `state_producer`
2. Internal state: `engine._step_anchor_time` → `engine._drift_corrector._anchor_time`
3. Internal state: `engine._step_count` → `engine._drift_corrector._count`
4. Internal state: `engine._drift_stats` → `engine._drift_corrector._stats`
5. ClockGenerator: `clock._clock_anchor_time` → `clock._drift_corrector._anchor_time`
6. ClockGenerator: `clock._pulse_count` → `clock._drift_corrector._count`
7. Drift reset: `await engine._handle_drift_reset()` → manual reset + stats update

**Tests migrated:**
- `test_timing_accuracy_10_seconds` (10-second timing accuracy)
- `test_timing_accuracy_30_seconds` (30-second long-running stability)
- `test_rapid_bpm_changes` (BPM change stress test)
- `test_extreme_bpm_changes` (extreme BPM values)
- `test_drift_reset_on_cpu_spike` (CPU spike recovery)
- `test_multiple_cpu_spikes` (multiple spike resilience)
- `test_concurrent_step_and_clock_loops` (concurrent loop synchronization)
- `test_comprehensive_stability_check` (comprehensive 2-second check)

**Result:** 383 passed with `RUN_STABILITY_TESTS=1` (59.4s), 375 passed default (1.7s)

---

## Future Work

**Phase 3 considerations:**
- ✅ ~~Remove skipped tests after service tests prove stable~~ (Completed 2026-03-13)
- Consider extracting NoteScheduler and CommandHandler if they grow
- Apply similar service extraction to other infrastructure components

---

## References

- Martin Fowler, *Refactoring: Improving the Design of Existing Code*, p.182 "Extract Class", p.106 "Extract Function"
- Robert C. Martin, *Clean Code*, Chapter 10 "Classes" - Single Responsibility Principle
- Related: ADR-0024 (Phase 1 code quality improvements)
- Related: ADR-0003 (Python Timing Engine - original drift correction implementation)
- Related: ADR-0008 (Overall code quality strategy)
