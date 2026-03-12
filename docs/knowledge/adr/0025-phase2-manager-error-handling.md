# ADR-0025: Phase 2 Code Quality - Manager Error Handling Standardization

**Status:** Accepted
**Date:** 2026-03-13
**Deciders:** Kengo Tobita, Claude Sonnet 4.5
**Related:** ADR-0024 (Phase 1 Code Quality Improvements), ADR-0008 (Code Quality Strategy)

---

## Context

Following Phase 1 code quality improvements (ADR-0024), Phase 2 continues the systematic refactoring initiative. This ADR addresses inconsistent error handling patterns in the domain layer's manager classes.

### Identified Issue

`PatternManager.create()` used a mixed error handling approach:

```python
def create(...) -> Optional[Pattern]:
    """Create a new pattern in a track.

    Returns:
        Created Pattern with server-generated pattern_id, or None if track not found

    Raises:
        ValueError: If validation fails
    """
    track = self._validate_pattern_creation(track_id, client_id)
    if track is None:
        return None  # ← Error Code pattern
    # ...
```

**Problems:**
1. **Inconsistent error handling:** Returns `None` for missing track but raises `ValueError` for missing client
2. **Error Code smell:** Callers must check for `None` return (Martin Fowler's "Replace Error Code with Exception", Refactoring p.310)
3. **Type safety:** `Optional[Pattern]` forces null checks throughout codebase
4. **API confusion:** Unclear when `None` is returned vs exception raised

**Impact on callers:**
```python
# Caller must handle None case
pattern = manager.create(track_id="invalid", ...)
if pattern is None:
    # Was it invalid track or something else?
    return error_response("Pattern creation failed")
```

---

## Decision

Apply **Replace Error Code with Exception** pattern (Refactoring, p.310) to standardize error handling.

### Solution: Exception-Based Error Handling

**Change 1: Raise ValueError for all validation failures**

```python
# Before
def _validate_pattern_creation(self, track_id: str, client_id: str) -> Optional[Track]:
    track = self.session.tracks.get(track_id)
    if track is None:
        return None  # Error code
    if client_id not in self.session.clients:
        raise ValueError(f"Client {client_id} does not exist")  # Exception
    return track

# After
def _validate_pattern_creation(self, track_id: str, client_id: str) -> Track:
    track = self.session.tracks.get(track_id)
    if track is None:
        raise ValueError(f"Track '{track_id}' not found")  # Consistent exceptions
    if client_id not in self.session.clients:
        raise ValueError(f"Client {client_id} does not exist")
    return track
```

**Change 2: Update return type to remove Optional**

```python
# Before
def create(...) -> Optional[Pattern]:
    track = self._validate_pattern_creation(track_id, client_id)
    if track is None:
        return None
    # ...

# After
def create(...) -> Pattern:
    track = self._validate_pattern_creation(track_id, client_id)
    # No None check needed - exception raised on failure
    # ...
```

### Benefits

1. **Consistent error handling:** All validation failures raise `ValueError`
2. **Clearer error flow:** Exceptions automatically propagate to caller
3. **Better type safety:** `Pattern` (not `Optional[Pattern]`) - no null checks needed
4. **Improved API clarity:** Method either succeeds (returns Pattern) or fails (raises exception)

### Updated API Contract

```python
def create(
    self,
    track_id: str,
    pattern_name: str,
    client_id: str,
    active: bool = True,
    events: Optional[list[PatternEvent]] = None,
) -> Pattern:
    """
    Create a new pattern in a track with server-generated ID.

    Args:
        track_id: Parent track ID (required)
        pattern_name: Human-readable name
        client_id: Owner client ID
        active: Whether pattern is active
        events: Initial events

    Returns:
        Created Pattern with server-generated pattern_id

    Raises:
        ValueError: If track not found or client doesn't exist
    """
```

---

## Consequences

### Positive

✅ **Consistency:** All manager validation failures now use exceptions
✅ **Type safety:** Eliminated `Optional` return type, reducing null checks
✅ **Clarity:** Clear contract - success returns value, failure raises exception
✅ **Maintainability:** Single error handling pattern across managers
✅ **Best practices:** Follows Martin Fowler's refactoring patterns

### Negative

⚠️ **Breaking change for direct callers:** Code checking for `None` must be updated
   - **Mitigation:** Tests updated to expect `ValueError`
   - **Impact:** Internal API only (no external users)

### Test Updates

```python
# Before
def test_create_pattern_invalid_track(self, container_with_client):
    result = container_with_client.patterns.create(
        track_id="invalid",
        pattern_name="main",
        client_id="client_001",
    )
    assert result is None

# After
def test_create_pattern_invalid_track(self, container_with_client):
    with pytest.raises(ValueError, match="Track 'invalid' not found"):
        container_with_client.patterns.create(
            track_id="invalid",
            pattern_name="main",
            client_id="client_001",
        )
```

---

## Implementation

**Files Modified:**
- `src/oiduna/domain/session/managers/pattern_manager.py`
  - `_validate_pattern_creation()`: Raise ValueError instead of returning None
  - `create()`: Return type `Pattern` instead of `Optional[Pattern]`
- `tests/domain/session/test_manager.py`
  - Updated test to expect `ValueError` exception

**Test Results:**
- All 70 manager tests pass
- Execution time: 0.39s

---

## References

- Martin Fowler, *Refactoring: Improving the Design of Existing Code*, p.310 "Replace Error Code with Exception"
- Related: ADR-0024 (Phase 1 code quality improvements)
- Related: ADR-0008 (Overall code quality strategy)
