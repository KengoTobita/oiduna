# ADR-0030: Replace `cycle` with `offset` for Micro-Timing

**Status:** Accepted
**Date:** 2026-03-16
**Deciders:** Kengo Tobita
**Related:** ADR-0020 (Timeline Lookahead), ADR-0028 (StepExecutor Extraction)

---

## Context

Oiduna's initial timing model used a `cycle: float` field (0.0-4.0 range, inherited from TidalCycles semantics) in both `PatternEvent` and `ScheduleEntry`. This design had several issues:

1. **BPM-dependent semantics**: Cycle values implied absolute positions in a 4-bar loop, making BPM changes conceptually complex.
2. **Limited micro-timing**: The cycle model didn't provide a clear way to express swing, triplets, or humanization within a single step.
3. **Confusing range**: The 0.0-4.0 range was arbitrary and not self-documenting.

### Use Case Requirements

We needed to support:
- **Swing timing**: Events at offset 0.0 and 0.66 within the same step (swung 16th notes)
- **Sub-step subdivision**: Multiple events within a single step (e.g., triplet feel: offsets 0.0, 0.333, 0.666)
- **Irregular meters (変拍子)**: Using step+offset combinations to express positions like 3/4 time on a 16-step grid
  - Example: Beats at absolute positions 0, 5.333, 10.666 steps
- **BPM independence**: Offset ratios remain constant when tempo changes

---

## Decision

Replace `cycle: float` with `offset: float [0.0, 1.0)` in both `PatternEvent` and `ScheduleEntry`.

### Offset Semantics

- **Range**: `[0.0, 1.0)` half-open interval (1.0 is excluded)
- **Meaning**: Relative position within a step
  - `0.0` = start of step (default)
  - `0.5` = halfway through step (swing)
  - `0.666` = 2/3 through step (sub-step subdivision)
  - `0.999...` = just before next step
- **BPM Independence**: Offset is a ratio, so it scales automatically with BPM changes

### Implementation Strategy

We chose **Option C: Apply offset at router/sender level** for several reasons:

1. **Separation of concerns**: Timing is a delivery concern, not a scheduling concern
2. **Matches DriftCorrector pattern**: Anchor-based timing model
3. **Easy to test**: Mock senders can verify timing without real hardware
4. **Future-proof**: Can evolve to OSC bundle timestamps if needed

### Key Changes

1. **Data Models** (src/oiduna/domain/models/events.py, src/oiduna/domain/schedule/models.py):
   - `PatternEvent.cycle` → `PatternEvent.offset` with validation `ge=0.0, lt=1.0`
   - `ScheduleEntry.cycle` → `ScheduleEntry.offset`
   - `from_dict()` defaults to `offset=0.0` for backward compatibility

2. **Timing Utilities** (src/oiduna/domain/models/timing.py):
   - Removed `CycleFloat` NewType
   - Removed `step_to_cycle()` and `cycle_to_step()` functions
   - Added `validate_offset()` function

3. **Execution Engine**:
   - **DriftCorrector**: Added `get_expected_time_with_offset()` method for sub-step timing
   - **StepExecutor**: Added `_send_messages_with_timing()` to group messages by offset
   - **DestinationRouter**: Added `send_messages_with_timing()` with `time.sleep()` delay

4. **API Layer**: Updated `ScheduleEntryRequest` in both timeline and playback routes

5. **Compilation**: Updated `SessionCompiler._create_message_from_event()` to use `offset`

### Timing Formula

```python
absolute_time = (step * step_duration) + (offset * step_duration)
step_duration = (60.0 / BPM) / 4  # seconds per step (1/16 note)
```

**Example** (120 BPM):
- `step_duration = 0.125s` (125ms)
- `offset=0.5` → 62.5ms delay within step
- `offset=0.666` → 83.3ms delay within step

### Irregular Meter Expression

While Oiduna uses a fixed 16-step bar grid, `step + offset` combinations enable flexible meter expression:

**3/4 time** (12 steps = 3 quarter notes):
- Beat 1: `(step=0, offset=0.0)` → absolute position 0 steps
- Beat 2: `(step=5, offset=0.333)` → absolute position 5.333 steps
- Beat 3: `(step=10, offset=0.666)` → absolute position 10.666 steps

This represents equally-spaced beats across an irregular division of the grid.

---

## Consequences

### Positive

1. **BPM-independent**: Offset ratios remain constant when tempo changes
2. **Self-documenting**: `[0.0, 1.0)` range is intuitive (percentage of step)
3. **Micro-timing support**: Enables swing, triplets, humanization without additional abstraction
4. **Flexible meter expression**: Can represent arbitrary beat positions using step+offset
5. **Clean timing model**: Matches DriftCorrector's anchor-based design

### Negative

1. **Breaking change**: No backward compatibility for `cycle` field
   - Migration: Use `offset=0.0` for old data
   - `from_dict()` provides default for missing offset
2. **Synchronous delay**: Current implementation uses `time.sleep()` (may block)
   - Mitigation: Can optimize to `asyncio.sleep()` if profiling shows issues

### Testing Impact

- **Removed**: 2 test classes (`TestStepToCycle`, `TestCycleToStep`) from `test_timing.py`
- **Updated**: 250+ test cases across 22 test files
- **Added**: `test_offset_validation.py` (7 tests), `test_swing_timing.py` (8 tests)

---

## Migration Path

For existing sessions with `cycle` values:

```python
# Before
PatternEvent(step=0, cycle=0.0, params={})
PatternEvent(step=64, cycle=1.0, params={})

# After
PatternEvent(step=0, offset=0.0, params={})
PatternEvent(step=64, offset=0.0, params={})  # cycle=1.0 → offset=0.0 (default)
```

**Note**: The `from_dict()` method provides a safe default (`offset=0.0`) for missing offset fields.

---

## Alternatives Considered

1. **Option A: Keep cycle, add separate offset field**
   - Rejected: Redundant, confusing dual timing model
2. **Option B: Apply offset at scheduler level**
   - Rejected: Violates separation of concerns (scheduler should be index-only)
3. **Option D: Use OSC bundle timestamps**
   - Deferred: Requires per-sender implementation, can be added later

---

## References

- Implementation PR: (to be filled)
- Related ADRs:
  - ADR-0020: Timeline Lookahead (execution architecture)
  - ADR-0028: StepExecutor Extraction (execution pipeline)
- External:
  - TidalCycles cycle semantics: https://tidalcycles.org/docs/patternlib/tutorials/cycle
  - SuperDirt timing expectations: https://github.com/musikinformatik/SuperDirt
