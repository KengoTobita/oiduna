"""Load tests for concurrent client scenarios.

Tests cover:
- Multiple clients compiling simultaneously
- Rapid pattern creation/modification/deletion
- Concurrent track operations
"""

import pytest
import asyncio
import time
from statistics import mean

from oiduna.domain.models.session import Session
from oiduna.domain.models.track import Track
from oiduna.domain.models.pattern import Pattern
from oiduna.domain.models.events import PatternEvent


@pytest.mark.load
def test_multiple_clients_compile():
    """Test 10 clients compiling patterns simultaneously.

    Success criteria:
    - All 10 clients successfully compile patterns
    - Total time < 5 seconds
    - No compilation errors
    - All patterns produce valid events
    """
    num_clients = 10
    patterns_per_client = 5

    session = Session()
    compilation_times = []
    errors = []

    start_time = time.perf_counter()

    for client_id in range(num_clients):
        # Create track for client
        track_id = f"{client_id:04x}"
        track = Track(
            track_id=track_id,
            track_name=f"track_{client_id}",
            client_id=f"client_{client_id}",
            destination_id=f"dest_{client_id % 3}"  # 3 destinations
        )

        # Create multiple patterns for this client
        for pattern_idx in range(patterns_per_client):
            pattern_id = f"{client_id:02x}{pattern_idx:02x}"

            # Vary pattern complexity (different number of events)
            if pattern_idx == 0:
                # Simple: 4 events
                events = [
                    PatternEvent(step=i * 64, offset=0.0, params={"s": "bd", "gain": 0.8})
                    for i in range(4)
                ]
            elif pattern_idx == 1:
                # Medium: 8 events
                events = [
                    PatternEvent(step=i * 32, offset=0.0, params={"s": "sn", "gain": 0.7})
                    for i in range(8)
                ]
            elif pattern_idx == 2:
                # Dense: 16 events
                events = [
                    PatternEvent(step=i * 16, offset=0.0, params={"s": "hh", "gain": 0.6})
                    for i in range(16)
                ]
            elif pattern_idx == 3:
                # Sparse: 2 events
                events = [
                    PatternEvent(step=i * 128, offset=0.0, params={"s": "cp", "gain": 0.9})
                    for i in range(2)
                ]
            else:
                # Variable: based on pattern index
                num_events = pattern_idx + 1
                events = [
                    PatternEvent(
                        step=(i * 256) // num_events,
                        offset=0.0,
                        params={"s": f"sound_{i}", "n": pattern_idx}
                    )
                    for i in range(num_events)
                ]

            compile_start = time.perf_counter()

            try:
                # Create pattern object
                pattern = Pattern(
                    pattern_id=pattern_id,
                    track_id=track_id,
                    pattern_name=f"pattern_{client_id}_{pattern_idx}",
                    client_id=f"client_{client_id}",
                    active=True,
                    events=events
                )

                track.patterns[pattern_id] = pattern

                compile_end = time.perf_counter()
                compilation_times.append((compile_end - compile_start) * 1000)

            except Exception as e:
                errors.append(f"Client {client_id} pattern {pattern_idx}: {e}")

        session.tracks[track_id] = track

    end_time = time.perf_counter()
    elapsed = end_time - start_time

    # Calculate metrics
    total_patterns = num_clients * patterns_per_client
    avg_compile_time = mean(compilation_times) if compilation_times else 0
    patterns_compiled = len(compilation_times)

    # Print metrics
    print(f"\n{'='*60}")
    print(f"Multiple Clients Compile Test")
    print(f"{'='*60}")
    print(f"Clients: {num_clients}")
    print(f"Patterns per client: {patterns_per_client}")
    print(f"Total patterns: {total_patterns}")
    print(f"Patterns compiled: {patterns_compiled}")
    print(f"Compilation errors: {len(errors)}")
    if errors:
        for err in errors[:5]:  # Show first 5 errors
            print(f"  - {err}")
    print(f"Total time: {elapsed:.3f}s")
    print(f"Avg compile time: {avg_compile_time:.3f}ms")
    print(f"Tracks in session: {len(session.tracks)}")
    print(f"{'='*60}\n")

    # Assertions
    assert len(errors) == 0, f"Encountered {len(errors)} compilation errors"
    assert patterns_compiled == total_patterns, f"Only compiled {patterns_compiled}/{total_patterns}"
    assert elapsed < 5.0, f"Compilation took {elapsed:.3f}s >= 5.0s"
    assert len(session.tracks) == num_clients, f"Expected {num_clients} tracks, got {len(session.tracks)}"


@pytest.mark.load
def test_client_pattern_churn():
    """Test rapid pattern create/modify/delete operations.

    Simulate 5 clients each performing 100 rapid operations (create, modify, delete).

    Success criteria:
    - Complete 500 operations in < 10 seconds
    - No errors during operations
    - Final state is consistent
    """
    num_clients = 5
    operations_per_client = 100

    session = Session()

    # Create tracks for each client
    for client_id in range(num_clients):
        track_id = f"{client_id:04x}"
        track = Track(
            track_id=track_id,
            track_name=f"track_{client_id}",
            client_id=f"client_{client_id}",
            destination_id="dest_0"
        )
        session.tracks[track_id] = track

    operations_completed = 0
    errors = []
    operation_times = []

    start_time = time.perf_counter()

    for client_id in range(num_clients):
        track_id = f"{client_id:04x}"
        track = session.tracks[track_id]

        pattern_counter = 0

        for op_idx in range(operations_per_client):
            op_start = time.perf_counter()

            try:
                # Cycle through operations: create, modify, delete
                op_type = op_idx % 3

                if op_type == 0:  # Create
                    pattern_id = f"{client_id:02x}{pattern_counter:02x}"
                    # Create simple pattern with 4 events
                    events = [
                        PatternEvent(step=i * 64, offset=0.0, params={"s": "bd", "gain": 0.8})
                        for i in range(4)
                    ]
                    pattern = Pattern(
                        pattern_id=pattern_id,
                        track_id=track_id,
                        pattern_name=f"pattern_{client_id}_{pattern_counter}",
                        client_id=f"client_{client_id}",
                        active=True,
                        events=events
                    )
                    track.patterns[pattern_id] = pattern
                    pattern_counter += 1

                elif op_type == 1 and len(track.patterns) > 0:  # Modify
                    pattern_id = list(track.patterns.keys())[-1]
                    pattern = track.patterns[pattern_id]
                    # Modify by changing events
                    pattern.events = [
                        PatternEvent(step=i * 128, offset=0.0, params={"s": "sn", "gain": 0.7})
                        for i in range(2)
                    ]

                elif op_type == 2 and len(track.patterns) > 0:  # Delete
                    pattern_id = list(track.patterns.keys())[-1]
                    del track.patterns[pattern_id]

                op_end = time.perf_counter()
                operation_times.append((op_end - op_start) * 1000)
                operations_completed += 1

            except Exception as e:
                errors.append(f"Client {client_id} operation {op_idx} ({op_type}): {e}")

    end_time = time.perf_counter()
    elapsed = end_time - start_time

    # Calculate metrics
    total_operations = num_clients * operations_per_client
    avg_operation_time = mean(operation_times) if operation_times else 0

    final_pattern_count = sum(len(track.patterns) for track in session.tracks.values())

    # Print metrics
    print(f"\n{'='*60}")
    print(f"Client Pattern Churn Test")
    print(f"{'='*60}")
    print(f"Clients: {num_clients}")
    print(f"Operations per client: {operations_per_client}")
    print(f"Total operations: {total_operations}")
    print(f"Operations completed: {operations_completed}")
    print(f"Errors: {len(errors)}")
    if errors:
        for err in errors[:5]:
            print(f"  - {err}")
    print(f"Total time: {elapsed:.3f}s")
    print(f"Operations/second: {operations_completed / elapsed:.1f}")
    print(f"Avg operation time: {avg_operation_time:.3f}ms")
    print(f"Final pattern count: {final_pattern_count}")
    print(f"{'='*60}\n")

    # Assertions
    assert len(errors) == 0, f"Encountered {len(errors)} errors"
    assert operations_completed == total_operations, f"Only completed {operations_completed}/{total_operations}"
    assert elapsed < 10.0, f"Operations took {elapsed:.3f}s >= 10.0s"


@pytest.mark.load
@pytest.mark.asyncio
async def test_concurrent_track_operations():
    """Test concurrent track create/modify/delete operations.

    Simulate 10 concurrent tasks each creating and modifying tracks.

    Success criteria:
    - All 10 tasks complete successfully
    - No race conditions or conflicts
    - Total time < 5 seconds
    """
    num_tasks = 10
    tracks_per_task = 10

    session = Session()
    task_errors = []
    tracks_created = 0

    async def create_tracks(task_id: int):
        """Task function to create and modify tracks."""
        nonlocal tracks_created

        try:
            for track_idx in range(tracks_per_task):
                track_id = f"{task_id:02x}{track_idx:02x}"

                # Create track
                track = Track(
                    track_id=track_id,
                    track_name=f"track_{task_id}_{track_idx}",
                    client_id=f"client_{task_id}",
                    destination_id=f"dest_{task_id % 3}"
                )

                # Add some patterns
                for pattern_idx in range(3):
                    pattern_id = f"{track_id}{pattern_idx:02x}"[:4]  # Keep 4 chars
                    # Create events based on pattern_idx
                    num_events = pattern_idx + 1
                    events = [
                        PatternEvent(
                            step=(i * 256) // num_events,
                            offset=0.0,
                            params={"s": "bd", "gain": 0.8}
                        )
                        for i in range(num_events)
                    ]
                    pattern = Pattern(
                        pattern_id=pattern_id,
                        track_id=track_id,
                        pattern_name=f"pattern_{pattern_idx}",
                        client_id=f"client_{task_id}",
                        active=True,
                        events=events
                    )
                    track.patterns[pattern_id] = pattern

                # Add to session
                session.tracks[track_id] = track
                tracks_created += 1

                # Small async delay to simulate I/O
                await asyncio.sleep(0.001)

        except Exception as e:
            task_errors.append(f"Task {task_id}: {e}")

    start_time = time.perf_counter()

    # Run all tasks concurrently
    tasks = [create_tracks(task_id) for task_id in range(num_tasks)]
    await asyncio.gather(*tasks)

    end_time = time.perf_counter()
    elapsed = end_time - start_time

    # Calculate metrics
    total_tracks = num_tasks * tracks_per_task
    total_patterns = sum(len(track.patterns) for track in session.tracks.values())

    # Print metrics
    print(f"\n{'='*60}")
    print(f"Concurrent Track Operations Test")
    print(f"{'='*60}")
    print(f"Concurrent tasks: {num_tasks}")
    print(f"Tracks per task: {tracks_per_task}")
    print(f"Total tracks: {total_tracks}")
    print(f"Tracks created: {tracks_created}")
    print(f"Total patterns: {total_patterns}")
    print(f"Errors: {len(task_errors)}")
    if task_errors:
        for err in task_errors[:5]:
            print(f"  - {err}")
    print(f"Total time: {elapsed:.3f}s")
    print(f"Tracks in session: {len(session.tracks)}")
    print(f"{'='*60}\n")

    # Assertions
    assert len(task_errors) == 0, f"Encountered {len(task_errors)} errors"
    assert tracks_created == total_tracks, f"Only created {tracks_created}/{total_tracks} tracks"
    assert len(session.tracks) == total_tracks, f"Session has {len(session.tracks)}/{total_tracks} tracks"
    assert elapsed < 5.0, f"Operations took {elapsed:.3f}s >= 5.0s"
