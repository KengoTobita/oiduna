# ADR-0028: Phase D2 - StepExecutor Service Extraction

## Status

**Accepted** - Implemented on 2026-03-15

## Context

Following Phase 2 (ADR-0026) which extracted DriftCorrector, ConnectionMonitor, and HeartbeatService from LoopEngine, the codebase required further refinement. The `_execute_current_step()` method (40 lines) contained 5 distinct responsibilities:

1. Timeline lookahead application (10 lines)
2. Message retrieval and filtering (15 lines)
3. Extension hook processing (15 lines)
4. Message routing (12 lines)
5. Periodic state updates (20 lines)

This violated the Single Responsibility Principle and made the step execution logic difficult to test in isolation.

### Goals

- Extract step execution pipeline into a dedicated service
- Reduce LoopEngine complexity and line count
- Improve testability of step execution logic
- Maintain consistency with Phase 2 service patterns
- Achieve >90% test coverage for extracted service

## Decision

### Extract StepExecutor Service

We extracted step execution logic into a new `StepExecutor` service following the same patterns established in Phase 2:

**Service Responsibilities:**
- Apply timeline changes with lookahead (ADR-0020)
- Retrieve messages from scheduler
- Filter messages by mute/solo state
- Apply extension hooks
- Route messages to destinations
- Publish periodic position/track updates

**LoopEngine Retains:**
- Main loop orchestration (`run()`, `_step_loop()`)
- Timing control and drift correction
- Service lifecycle management
- Public API methods
- Dependency injection container

### Architecture Pattern

**Protocol-Based Dependency Injection:**
```python
class MessageScheduler(Protocol):
    @property
    def message_count(self) -> int: ...
    def get_messages_at_step(self, step: int) -> list[Any]: ...

class MessageRouter(Protocol):
    def send_messages(self, messages: list[Any]) -> None: ...

class StatePublisher(Protocol):
    async def send_position(...) -> None: ...
    async def send_tracks(...) -> None: ...
    async def send_error(...) -> None: ...

class MessageFilter(Protocol):
    def filter_messages(self, messages: list[Any]) -> list[Any]: ...
    @property
    def position(self) -> Any: ...
    @property
    def playback_state(self) -> Any: ...

class TimelineProvider(Protocol):
    @property
    def timeline(self) -> Any: ...
    @property
    def global_step(self) -> int: ...
```

**StepExecutor Implementation:**
```python
class StepExecutor:
    TIMELINE_LOOKAHEAD_STEPS = 32  # 2 bar lookahead
    TIMELINE_MIN_LOOKAHEAD = 8     # 2 beat minimum

    def __init__(
        self,
        message_scheduler: MessageScheduler,
        message_router: MessageRouter,
        state_publisher: StatePublisher,
        message_filter: MessageFilter,
        timeline_provider: TimelineProvider,
        session_loaded_check: Callable[[], bool],
        get_tracks_info: Callable[[], list[dict[str, Any]]],
        position_update_interval: str = "beat",
        before_send_hooks: list[Callable] | None = None,
    ):
        # Store dependencies
        ...

    async def execute_step(self, current_step: int, current_bpm: float) -> None:
        """Execute complete step processing pipeline."""
        try:
            await self._apply_timeline_lookahead()
            messages = self._get_filtered_messages(current_step)
            if messages:
                messages = self._apply_hooks(messages, current_step, current_bpm)
                self._send_messages(messages, current_step)
            await self._publish_periodic_updates(current_step, current_bpm)
        except Exception as e:
            logger.error(f"Step processing error: {e}")
            await self._state_publisher.send_error("STEP_ERROR", str(e))
```

**LoopEngine Integration:**
```python
class LoopEngine:
    def __init__(self, ...):
        # Phase D2: Step executor service (initialized in start())
        self._step_executor: StepExecutor | None = None

    def start(self) -> None:
        # Initialize step executor
        if self._step_executor is None:
            self._step_executor = StepExecutor(
                message_scheduler=self._loop_scheduler,
                message_router=self._destination_router,
                state_publisher=self._state_producer,
                message_filter=self.state,  # RuntimeState
                timeline_provider=self,  # LoopEngine implements protocol
                session_loaded_check=lambda: self._session_loader.destinations_loaded,
                get_tracks_info=self._get_tracks_info,
                position_update_interval=self.state.position_update_interval,
                before_send_hooks=self._before_send_hooks,
            )
        ...

    async def _step_loop(self) -> None:
        """16th note step loop (simplified)."""
        while self._running:
            if not self.state.playing:
                self._drift_corrector.reset()
                await asyncio.sleep(0.001)
                continue

            should_reset, _ = await self._drift_corrector.check_drift(...)
            if should_reset:
                await asyncio.sleep(step_duration)
                continue

            # Execute current step (Phase D2: delegated to StepExecutor)
            if self._step_executor:
                await self._step_executor.execute_step(
                    self.state.position.step,
                    self.state.bpm,
                )

            await self._wait_for_next_step()
```

### Test Strategy

Following the pattern from `test_drift_corrector.py`:

**Mock Objects:**
- `MockMessageScheduler`: Simulates message scheduling
- `MockMessageRouter`: Tracks sent messages
- `MockStatePublisher`: Records state updates
- `MockMessageFilter`: Simulates mute/solo filtering
- `MockTimelineProvider`: Provides timeline access

**Test Coverage:**
- Basic step execution (4 tests)
- Message filtering (2 tests)
- Extension hook application (2 tests)
- Periodic updates (4 tests)
- Session loaded gate (1 test)
- Error handling (2 tests)
- Timeline lookahead (2 tests)

**Result:** 17 tests, 100% code coverage

## Consequences

### Positive

1. **Reduced Complexity**
   - LoopEngine: 928 → 841 lines (-9.4%)
   - Removed 5 methods (~102 lines)
   - `_step_loop()` simplified and clarified
   - Single clear delegation point

2. **Improved Testability**
   - StepExecutor can be tested in isolation
   - 100% test coverage achieved
   - Mock dependencies clearly defined
   - Easy to verify step execution behavior

3. **Better Separation of Concerns**
   - LoopEngine: Orchestration and timing
   - StepExecutor: Step processing pipeline
   - Clear responsibility boundaries
   - Easier to understand and maintain

4. **Consistency with Phase 2**
   - Same Protocol-based DI pattern
   - Similar service structure
   - Comparable test patterns
   - Uniform architecture

5. **Maintainability**
   - Easier to modify step execution logic
   - Changes don't affect timing control
   - Clear extension points
   - Well-documented responsibilities

### Neutral

1. **Indirection**
   - One more layer of abstraction
   - Method call overhead (negligible)
   - More files to navigate

2. **Service Count**
   - Now 4 services (was 3)
   - Increased service coordination
   - More initialization code

### Negative

1. **Initial Learning Curve**
   - New developers need to understand service architecture
   - More protocols to learn
   - Delegation pattern requires understanding

## Metrics

### Before Phase D2

| Metric | Value |
|--------|-------|
| LoopEngine lines | 928 |
| `_step_loop()` lines | 35 |
| `_execute_current_step()` lines | 40 |
| Total services | 3 |
| Test count | 454 |

### After Phase D2

| Metric | Value | Change |
|--------|-------|--------|
| LoopEngine lines | 841 | **-9.4%** |
| `_step_loop()` lines | 28 | **-20%** |
| StepExecutor lines | 291 | New |
| Total services | 4 | +1 |
| Test count | 471 | +17 |
| StepExecutor coverage | 100% | ✅ |

### Net Impact

- **Code reduction**: 928 → 841 (-87 lines, -9.4%)
- **Complexity reduction**: `_step_loop()` simplified by 20%
- **Test coverage**: +17 tests, 100% coverage for new service
- **All tests pass**: 471 passed, 8 skipped

## Implementation Notes

### Files Modified

**New Files:**
- `src/oiduna/infrastructure/execution/services/step_executor.py` (291 lines)
- `tests/infrastructure/execution/services/test_step_executor.py` (383 lines)

**Modified Files:**
- `src/oiduna/infrastructure/execution/loop_engine.py` (-87 lines)
- `src/oiduna/infrastructure/execution/services/__init__.py` (+14 lines)

**Total Impact:**
- Production code: +204 lines (new service)
- Test code: +383 lines (comprehensive tests)
- Net reduction in LoopEngine: -87 lines

### Removed from LoopEngine

1. Methods:
   - `_execute_current_step()` (40 lines)
   - `_get_filtered_messages()` (16 lines)
   - `_apply_hooks()` (15 lines)
   - `_send_messages()` (14 lines)
   - `_publish_periodic_updates()` (21 lines)

2. Constants:
   - `TIMELINE_LOOKAHEAD_STEPS` (moved to StepExecutor)
   - `TIMELINE_MIN_LOOKAHEAD` (moved to StepExecutor)

### Integration Points

**LoopEngine provides:**
- `timeline` property (implements TimelineProvider)
- `global_step` property (implements TimelineProvider)
- `state` (RuntimeState, implements MessageFilter)
- `_loop_scheduler` (LoopScheduler, implements MessageScheduler)
- `_destination_router` (DestinationRouter, implements MessageRouter)
- `_state_producer` (StateProducer, implements StatePublisher)
- `_session_loader.destinations_loaded` (session gate)
- `_get_tracks_info()` (track information)
- `_before_send_hooks` (extension hooks)

## Related ADRs

- **ADR-0026**: Phase 2 LoopEngine Service Extraction (DriftCorrector, ConnectionMonitor, HeartbeatService)
- **ADR-0020**: Timeline Lookahead Architecture
- **ADR-0008**: Code Quality Refactoring Strategy

## References

- Martin Fowler: "Extract Class" refactoring pattern
- Robert C. Martin: Single Responsibility Principle
- Phase 2 implementation: DriftCorrector service pattern
