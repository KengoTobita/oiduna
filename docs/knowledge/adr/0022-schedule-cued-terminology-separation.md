# ADR-0022: Schedule/Cued Terminology Separation

**Date**: 2026-03-11
**Status**: Accepted
**Deciders**: Development Team

## Context

### Problem Statement

The codebase had two different concepts both using "Scheduled" terminology, causing confusion:

1. **ScheduledMessageBatch/ScheduledMessage** - Immutable 256-step execution plan
   - Meaning: "placement is complete" (past participle)
   - State: Frozen, compiled once
   - Used by: Loop execution engine

2. **ScheduledChange** - Future pattern change reservation
   - Meaning: "reserved for future" (adjective)
   - State: Mutable, can be cancelled
   - Used by: Timeline scheduling system

This dual usage created cognitive dissonance:
- Same word ("Scheduled") for opposite temporal states
- Past-complete vs future-pending
- Immutable vs mutable
- Execution plan vs reservation

### Real-World Analogy Mismatch

```
"Scheduled train departure" (確定済みの時刻表)
vs
"Scheduled meeting" (予約された会議)
```

These are fundamentally different concepts forced into the same terminology.

## Decision

We separate the terminology to match their semantic roles:

### Schedule Subsystem (Immutable Execution Plan)

**Renamed**:
- `ScheduledMessageBatch` → `LoopSchedule`
- `ScheduledMessage` → `ScheduleEntry`
- `MessageScheduler` → `LoopScheduler`

**Rationale**:
- "Schedule" (noun) = timetable, fixed plan
- Like a train schedule - once published, it's fixed
- Emphasizes the 256-step loop nature
- Clear that this is the execution plan

**Real-world analogy**: Train timetable
- Published once
- Immutable
- Consulted repeatedly
- Step-by-step execution

### Cued Subsystem (Future Reservations)

**Renamed**:
- `ScheduledChange` → `CuedChange`
- `ScheduledChangeTimeline` → `CuedChangeTimeline`
- `schedule_change()` → `cue_change()`
- `scheduled_at` → `cued_at`

**Rationale**:
- "Cued" (adjective) = next in line, prepared
- DJ terminology: "cue the next track"
- Emphasizes future execution
- Musical context matches live coding workflow

**Real-world analogy**: DJ cue list
- Prepared but not yet playing
- Can be modified/cancelled
- Executed when the time comes
- Multiple tracks can be cued

## Consequences

### Positive

1. **Semantic Clarity**
   - Schedule = confirmed execution plan
   - Cued = future reservation
   - No more temporal confusion

2. **Musical Context**
   - "Cue" is familiar to musicians/DJs
   - Matches live coding mental model
   - Natural for performance context

3. **Code Readability**
   ```python
   # Clear: compiling to execution plan
   schedule = compiler.compile(session)

   # Clear: cueing future change
   timeline.cue_change(change, current_step)
   ```

4. **Type Safety**
   - No accidental mixing of concepts
   - Clearer API boundaries
   - Better autocomplete hints

### Negative

1. **Breaking Change**
   - All existing code must migrate
   - API endpoints changed (`/timeline/schedule` → `/timeline/cue`)
   - JSON field names changed (`scheduled_at` → `cued_at`)

2. **Learning Curve**
   - New terminology to learn
   - Documentation must be updated
   - Migration guide required

### Neutral

1. **Testing**
   - All 255 tests still pass
   - No functionality changed
   - Only names changed

## Implementation

### Changed Files (50 files total)

**Core Models** (8 files):
- `oiduna_scheduler/scheduler_models.py`
- `oiduna_scheduler/scheduler.py`
- `oiduna_scheduler/__init__.py`
- `oiduna_timeline/models.py`
- `oiduna_timeline/timeline.py`
- `oiduna_timeline/merger.py`
- `oiduna_timeline/__init__.py`
- `oiduna_models/events.py`

**Usage Sites** (22 files):
- Loop Engine (4 files)
- Session Layer (5 files)
- API Layer (3 files)
- Other packages (10 files)

**Tests** (15 files):
- Timeline tests (3 files)
- Session tests (7 files)
- Models tests (5 files)

**Documentation** (5 files):
- `MIGRATION_GUIDE_SCHEDULE_CUED.md` (new)
- `TERMINOLOGY.md` (updated v2.0→v3.0)
- `CODING_CONVENTIONS.md` (updated)
- `architecture/DIAGRAMS.md` (updated)
- `README.md` (updated)

### Backward Compatibility

**Decision**: Complete removal (no compatibility layer)

**Rationale**:
- Clean break prevents lingering confusion
- Forces intentional migration
- Prevents accidental use of old names
- Project is in active development phase

### Migration Path

1. **Search and Replace**
   - Provided automated scripts in migration guide
   - ~1050 lines changed across 50 files

2. **Testing**
   - All 255 tests pass ✅
   - No functionality regression

3. **Documentation**
   - Comprehensive migration guide
   - Updated terminology reference
   - Architecture diagrams updated

## Alternatives Considered

### Alternative 1: Keep Status Quo

**Rejected**: Confusion would persist and compound

### Alternative 2: Use "Compiled" instead of "Schedule"

```python
CompiledLoop / CompiledEntry
```

**Rejected**:
- Too developer-centric
- Loses musical context
- Doesn't emphasize execution plan nature

### Alternative 3: Use "Timeline" for both

```python
ExecutionTimeline / EventTimeline
```

**Rejected**:
- "Timeline" is too generic
- Doesn't distinguish immutable vs mutable
- Already used for Timeline scheduling system

### Alternative 4: Keep "Scheduled" with qualifiers

```python
CompiledSchedule / FutureSchedule
```

**Rejected**:
- Still contains "Schedule" ambiguity
- Qualifiers get dropped in conversation
- Doesn't solve root problem

## Verification

### Test Results

```bash
✅ 255/255 tests passed (100%)

Breakdown:
- oiduna_timeline: 39/39 passed
- oiduna_session: 83/83 passed
- oiduna_models: 133/133 passed
```

### Type Check

```bash
✅ mypy: No errors in modified packages
```

### Coverage

```bash
No functionality changes
→ Coverage maintained at previous levels
```

## Related ADRs

- [ADR-0017: IPC and Session Naming Standardization](0017-ipc-and-session-naming-standardization.md) - SessionEvent → SessionChange
- [ADR-0021: Backward Compatibility Removal](0021-backward-compatibility-removal.md) - Clean break policy
- [ADR-0010: SessionContainer Refactoring](0010-session-container-refactoring.md) - Manager pattern

## References

### Migration Guide

See [MIGRATION_GUIDE_SCHEDULE_CUED.md](../../MIGRATION_GUIDE_SCHEDULE_CUED.md)

### Terminology

See [TERMINOLOGY.md](../../TERMINOLOGY.md) - Schedule/Cued section

### Code Examples

**Before**:
```python
# Confusing: both use "Scheduled"
batch = ScheduledMessageBatch(messages=(...), bpm=120)
change = ScheduledChange(batch=batch, target_global_step=1000)
```

**After**:
```python
# Clear: Schedule vs Cued
schedule = LoopSchedule(entries=(...), bpm=120)
change = CuedChange(batch=schedule, target_global_step=1000)
```

## Notes

### Musical Context

The "Cued" terminology draws from DJ/musician workflows:
- DJs "cue" tracks before playing them
- Live coders "queue up" pattern changes
- Musicians "prepare" the next section

This matches the mental model of live coding where changes are prepared ahead of time and executed at the right moment.

### Implementation Timeline

- **2026-03-11**: Decision made
- **2026-03-11**: Implementation completed
- **2026-03-11**: Tests passing, documentation updated
- **2026-03-11**: ADR written

### Contributors

- Primary implementation: Claude Sonnet 4.5
- Decision: Development team consensus
- User feedback: Proactive cleanup request

---

**Supersedes**: None (new terminology)
**Superseded by**: None (current)
