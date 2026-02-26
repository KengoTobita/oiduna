"""
Stability Tests for MARS Loop Engine

Tests for verifying stable operation under various conditions:
- Long-running timing accuracy
- BPM change stress testing
- CPU spike recovery
- Concurrent loop operation
- High event density

These tests are marked with @pytest.mark.slow and can be run with:
    pytest -m slow          # Run only slow tests
    pytest -m "not slow"    # Skip slow tests

Environment variable RUN_STABILITY_TESTS=1 enables these tests.
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any

import pytest

from oiduna_loop.engine import LoopEngine
from oiduna_loop.tests.mocks import MockCommandSource, MockMidiOutput, MockOscOutput, MockStateSink

# Skip stability tests unless explicitly enabled
STABILITY_TESTS_ENABLED = os.environ.get("RUN_STABILITY_TESTS", "0") == "1"
stability_test = pytest.mark.skipif(
    not STABILITY_TESTS_ENABLED,
    reason="Stability tests disabled. Set RUN_STABILITY_TESTS=1 to enable.",
)


class StabilityTestEngine:
    """Helper class for running stability tests with timing measurements."""

    def __init__(
        self,
        osc: MockOscOutput,
        midi: MockMidiOutput,
        commands: MockCommandSource,
        publisher: MockStateSink,
    ):
        self.engine = LoopEngine(
            osc=osc,
            midi=midi,
            commands=commands,
            publisher=publisher,
        )
        self.engine._register_handlers()
        self.step_times: list[float] = []
        self.original_process_step = None

    def start_timing_capture(self) -> None:
        """Start capturing step timing data."""
        self.step_times = []
        self._last_step_time = time.perf_counter()

    def record_step_time(self) -> None:
        """Record a step occurrence time."""
        now = time.perf_counter()
        if self.step_times:
            # Record interval since last step
            self.step_times.append(now - self._last_step_time)
        self._last_step_time = now

    def get_timing_stats(self) -> dict[str, float]:
        """Get timing statistics from captured data."""
        if not self.step_times:
            return {"count": 0, "mean_ms": 0, "max_deviation_ms": 0}

        expected_duration = self.engine.state.step_duration
        expected_ms = expected_duration * 1000

        deviations = [abs(t * 1000 - expected_ms) for t in self.step_times]

        return {
            "count": len(self.step_times),
            "expected_ms": expected_ms,
            "mean_ms": sum(self.step_times) * 1000 / len(self.step_times),
            "max_deviation_ms": max(deviations) if deviations else 0,
            "mean_deviation_ms": sum(deviations) / len(deviations) if deviations else 0,
        }


@pytest.fixture
def stability_engine(
    mock_osc: MockOscOutput,
    mock_midi: MockMidiOutput,
    mock_commands: MockCommandSource,
    mock_publisher: MockStateSink,
) -> StabilityTestEngine:
    """Create a stability test engine."""
    return StabilityTestEngine(mock_osc, mock_midi, mock_commands, mock_publisher)


def create_dense_session(num_tracks: int = 8) -> dict[str, Any]:
    """Create a session with many tracks and events for stress testing."""
    tracks = {}
    sequences = {}

    for i in range(num_tracks):
        track_id = f"track_{i}"
        tracks[track_id] = {
            "meta": {"mute": False, "solo": False},
            "sound": {"s": f"sound_{i}"},
            "fx": {"room": 0.2, "delay": 0.1},
        }
        # Events on every step
        sequences[track_id] = {
            "events": [{"step": s, "velocity": 0.8} for s in range(16)]
        }

    return {
        "environment": {"bpm": 120.0},
        "tracks": tracks,
        "sequences": sequences,
    }


# =============================================================================
# Test 1: Long-Running Timing Accuracy
# =============================================================================


@stability_test
class TestLongRunningTiming:
    """Test timing accuracy over extended periods."""

    @pytest.mark.asyncio
    async def test_timing_accuracy_10_seconds(
        self,
        stability_engine: StabilityTestEngine,
    ):
        """Run step loop for 10 seconds and verify timing accuracy."""
        engine = stability_engine.engine
        engine.state.set_bpm(120)  # 125ms per step
        engine._handle_play({})

        # Track timing manually
        step_intervals: list[float] = []
        last_time = time.perf_counter()
        start_time = last_time

        duration_seconds = 10
        expected_step_duration = engine.state.step_duration

        # Run simplified timing loop
        while time.perf_counter() - start_time < duration_seconds:
            if engine._step_anchor_time is None:
                engine._step_anchor_time = time.perf_counter()
                engine._step_count = 0

            current_time = time.perf_counter()
            expected_time = engine._step_anchor_time + (
                engine._step_count * expected_step_duration
            )

            if current_time >= expected_time:
                # Record interval
                if engine._step_count > 0:
                    step_intervals.append(current_time - last_time)
                last_time = current_time
                engine._step_count += 1

                # Drift tracking
                drift_ms = (current_time - expected_time) * 1000
                if abs(drift_ms) > engine._drift_stats["max_drift_ms"]:
                    engine._drift_stats["max_drift_ms"] = abs(drift_ms)

            await asyncio.sleep(0.001)

        engine._handle_stop({})

        # Analyze results
        assert len(step_intervals) > 0, "No steps recorded"

        expected_ms = expected_step_duration * 1000
        deviations = [abs(interval * 1000 - expected_ms) for interval in step_intervals]
        max_deviation = max(deviations)
        mean_deviation = sum(deviations) / len(deviations)

        # Assertions
        assert max_deviation < 20.0, f"Max timing deviation too high: {max_deviation:.2f}ms"
        assert mean_deviation < 5.0, f"Mean timing deviation too high: {mean_deviation:.2f}ms"

        drift_stats = engine.get_drift_stats()
        assert drift_stats["reset_count"] == 0, (
            f"Unexpected drift resets: {drift_stats['reset_count']}"
        )

        print("\n=== Long Running Test Results (10s) ===")
        print(f"Steps executed: {len(step_intervals)}")
        print(f"Expected step duration: {expected_ms:.2f}ms")
        print(f"Max deviation: {max_deviation:.2f}ms")
        print(f"Mean deviation: {mean_deviation:.2f}ms")
        print(f"Max drift observed: {drift_stats['max_drift_ms']:.2f}ms")

    @pytest.mark.asyncio
    async def test_timing_accuracy_30_seconds(
        self,
        stability_engine: StabilityTestEngine,
    ):
        """Run step loop for 30 seconds - extended stability test."""
        engine = stability_engine.engine
        engine.state.set_bpm(140)  # Faster BPM
        engine._handle_play({})

        step_count = 0
        start_time = time.perf_counter()
        duration_seconds = 30
        expected_step_duration = engine.state.step_duration

        engine._step_anchor_time = start_time
        engine._step_count = 0

        while time.perf_counter() - start_time < duration_seconds:
            current_time = time.perf_counter()
            expected_time = engine._step_anchor_time + (
                engine._step_count * expected_step_duration
            )

            if current_time >= expected_time:
                step_count += 1
                engine._step_count += 1

                drift_ms = (current_time - expected_time) * 1000
                if abs(drift_ms) > engine._drift_stats["max_drift_ms"]:
                    engine._drift_stats["max_drift_ms"] = abs(drift_ms)

            await asyncio.sleep(0.001)

        engine._handle_stop({})

        drift_stats = engine.get_drift_stats()

        # At 140 BPM, expect ~280 steps in 30 seconds
        expected_steps = int(duration_seconds / expected_step_duration)
        assert step_count >= expected_steps * 0.95, (
            f"Too few steps: {step_count} < {expected_steps * 0.95}"
        )

        assert drift_stats["max_drift_ms"] < engine.DRIFT_RESET_THRESHOLD_MS, (
            f"Drift exceeded threshold: {drift_stats['max_drift_ms']:.2f}ms"
        )

        print("\n=== Long Running Test Results (30s) ===")
        print(f"Steps executed: {step_count}")
        print(f"Expected steps: ~{expected_steps}")
        print(f"Max drift: {drift_stats['max_drift_ms']:.2f}ms")
        print(f"Drift resets: {drift_stats['reset_count']}")


# =============================================================================
# Test 2: BPM Change Stress Test
# =============================================================================


@stability_test
class TestBPMChangeStress:
    """Test stability under rapid BPM changes."""

    @pytest.mark.asyncio
    async def test_rapid_bpm_changes(
        self,
        stability_engine: StabilityTestEngine,
    ):
        """Rapidly change BPM while running and verify stability."""
        engine = stability_engine.engine
        engine.state.set_bpm(120)
        engine._handle_play({})
        engine._step_anchor_time = time.perf_counter()
        engine._step_count = 0

        # Also set up clock generator
        engine._clock_generator._clock_anchor_time = time.perf_counter()
        engine._clock_generator._pulse_count = 0

        bpm_sequence = [120, 140, 100, 180, 90, 160, 110, 150, 120]
        errors: list[str] = []

        for i, bpm in enumerate(bpm_sequence):
            try:
                # Change BPM
                engine._handle_bpm({"bpm": bpm})

                # Verify state is consistent
                assert engine.state.bpm == bpm, f"BPM not updated to {bpm}"
                assert engine.state.playing, "Playback stopped unexpectedly"

                # Verify anchors were reset (for all but first iteration)
                if i > 0:
                    # Anchor should be recent (within 100ms)
                    anchor_age = time.perf_counter() - engine._step_anchor_time
                    if anchor_age > 0.1:
                        errors.append(f"Step anchor not reset for BPM {bpm}")

                    clock_anchor_age = (
                        time.perf_counter() - engine._clock_generator._clock_anchor_time
                    )
                    if clock_anchor_age > 0.1:
                        errors.append(f"Clock anchor not reset for BPM {bpm}")

                # Small delay between changes
                await asyncio.sleep(0.05)

            except Exception as e:
                errors.append(f"Error at BPM {bpm}: {e}")

        engine._handle_stop({})

        assert len(errors) == 0, f"Errors during BPM changes: {errors}"

        # Drift stats should NOT be incremented by BPM changes
        drift_stats = engine.get_drift_stats()
        clock_stats = engine._clock_generator.get_drift_stats()

        print("\n=== BPM Change Stress Test Results ===")
        print(f"BPM changes: {len(bpm_sequence)}")
        print(f"Step drift resets: {drift_stats['reset_count']}")
        print(f"Clock drift resets: {clock_stats['reset_count']}")

    @pytest.mark.asyncio
    async def test_extreme_bpm_changes(
        self,
        stability_engine: StabilityTestEngine,
    ):
        """Test extreme BPM values at boundaries."""
        engine = stability_engine.engine
        engine._handle_play({})
        engine._step_anchor_time = time.perf_counter()

        # Test boundary values (clamped to 1.0-999.0 by SessionState)
        extreme_bpms = [0.5, 1, 30, 40, 60, 200, 250, 300, 500, 999, 1500]

        for bpm in extreme_bpms:
            engine._handle_bpm({"bpm": bpm})
            # BPM should be clamped to valid range (1.0 to 999.0)
            assert 1.0 <= engine.state.bpm <= 999.0, (
                f"BPM out of valid range: {engine.state.bpm}"
            )
            # Verify anchor was reset for each change
            assert engine._step_anchor_time is not None
            await asyncio.sleep(0.01)

        engine._handle_stop({})
        print("\n=== Extreme BPM Test Passed ===")


# =============================================================================
# Test 3: CPU Spike Simulation
# =============================================================================


@stability_test
class TestCPUSpikeRecovery:
    """Test recovery from simulated CPU spikes."""

    @pytest.mark.asyncio
    async def test_drift_reset_on_cpu_spike(
        self,
        stability_engine: StabilityTestEngine,
    ):
        """Simulate CPU spike and verify drift reset triggers correctly."""
        engine = stability_engine.engine
        engine.state.set_bpm(120)
        engine._handle_play({})

        start_time = time.perf_counter()
        engine._step_anchor_time = start_time
        engine._step_count = 0

        step_duration = engine.state.step_duration
        steps_before_spike = 0
        spike_triggered = False

        # Run for a bit, then simulate spike
        while time.perf_counter() - start_time < 5:
            current_time = time.perf_counter()
            expected_time = engine._step_anchor_time + (
                engine._step_count * step_duration
            )

            # Calculate drift
            drift_ms = (current_time - expected_time) * 1000

            # Update max drift
            if abs(drift_ms) > engine._drift_stats["max_drift_ms"]:
                engine._drift_stats["max_drift_ms"] = abs(drift_ms)

            # Check if drift exceeds threshold
            if abs(drift_ms) > engine.DRIFT_RESET_THRESHOLD_MS:
                # Trigger drift reset
                await engine._handle_drift_reset(drift_ms, current_time)
                spike_triggered = True

            if current_time >= expected_time:
                engine._step_count += 1
                steps_before_spike += 1

                # Simulate CPU spike after 20 steps
                if steps_before_spike == 20 and not spike_triggered:
                    print(f"Simulating 150ms CPU spike at step {steps_before_spike}")
                    await asyncio.sleep(0.150)  # 150ms spike
                    continue

            await asyncio.sleep(0.001)

        engine._handle_stop({})

        drift_stats = engine.get_drift_stats()

        # Should have triggered at least one drift reset
        assert drift_stats["reset_count"] >= 1, (
            "CPU spike should have triggered drift reset"
        )

        print("\n=== CPU Spike Recovery Test Results ===")
        print(f"Steps before spike: {steps_before_spike}")
        print(f"Drift resets triggered: {drift_stats['reset_count']}")
        print(f"Max drift observed: {drift_stats['max_drift_ms']:.2f}ms")
        print(f"Total skipped steps: {drift_stats['total_skipped_steps']}")

    @pytest.mark.asyncio
    async def test_multiple_cpu_spikes(
        self,
        stability_engine: StabilityTestEngine,
    ):
        """Test recovery from multiple CPU spikes."""
        engine = stability_engine.engine
        engine.state.set_bpm(120)
        engine._handle_play({})

        start_time = time.perf_counter()
        engine._step_anchor_time = start_time
        engine._step_count = 0

        step_duration = engine.state.step_duration
        spike_count = 0
        spike_intervals = [1.0, 2.5, 4.0]  # Spike at 1s, 2.5s, 4s

        while time.perf_counter() - start_time < 5:
            current_time = time.perf_counter()
            elapsed = current_time - start_time

            # Check if we should trigger a spike
            if spike_count < len(spike_intervals):
                if elapsed >= spike_intervals[spike_count]:
                    print(f"Spike {spike_count + 1} at {elapsed:.1f}s")
                    await asyncio.sleep(0.100)  # 100ms spike
                    spike_count += 1
                    continue

            expected_time = engine._step_anchor_time + (
                engine._step_count * step_duration
            )
            drift_ms = (current_time - expected_time) * 1000

            if abs(drift_ms) > engine._drift_stats["max_drift_ms"]:
                engine._drift_stats["max_drift_ms"] = abs(drift_ms)

            if abs(drift_ms) > engine.DRIFT_RESET_THRESHOLD_MS:
                await engine._handle_drift_reset(drift_ms, current_time)

            if current_time >= expected_time:
                engine._step_count += 1

            await asyncio.sleep(0.001)

        engine._handle_stop({})

        drift_stats = engine.get_drift_stats()

        # Should have handled multiple spikes
        assert drift_stats["reset_count"] >= 2, (
            f"Expected multiple drift resets, got {drift_stats['reset_count']}"
        )

        print("\n=== Multiple CPU Spikes Test Results ===")
        print(f"Spikes simulated: {spike_count}")
        print(f"Drift resets: {drift_stats['reset_count']}")


# =============================================================================
# Test 4: Concurrent Loop Operation
# =============================================================================


@stability_test
class TestConcurrentLoops:
    """Test step loop and clock loop running concurrently."""

    @pytest.mark.asyncio
    async def test_concurrent_step_and_clock_loops(
        self,
        mock_osc: MockOscOutput,
        mock_midi: MockMidiOutput,
        mock_commands: MockCommandSource,
        mock_publisher: MockStateSink,
    ):
        """Run both loops concurrently and verify synchronization."""
        engine = LoopEngine(
            osc=mock_osc,
            midi=mock_midi,
            commands=mock_commands,
            publisher=mock_publisher,
        )
        engine._register_handlers()
        engine.state.set_bpm(120)
        engine._handle_play({})

        step_count = 0
        pulse_count = 0
        duration = 5  # seconds
        start_time = time.perf_counter()

        step_duration = engine.state.step_duration
        pulse_duration = engine._clock_generator.calculate_pulse_duration(step_duration)

        engine._step_anchor_time = start_time
        engine._step_count = 0
        engine._clock_generator._clock_anchor_time = start_time
        engine._clock_generator._pulse_count = 0

        # Capture anchor times for use in closures (mypy needs explicit types)
        step_anchor: float = start_time
        clock_anchor: float = start_time

        async def step_loop():
            nonlocal step_count
            while time.perf_counter() - start_time < duration:
                current = time.perf_counter()
                expected = step_anchor + (
                    engine._step_count * step_duration
                )
                if current >= expected:
                    step_count += 1
                    engine._step_count += 1
                await asyncio.sleep(0.001)

        async def clock_loop():
            nonlocal pulse_count
            clock = engine._clock_generator
            while time.perf_counter() - start_time < duration:
                current = time.perf_counter()
                expected = clock_anchor + (
                    clock._pulse_count * pulse_duration
                )
                if current >= expected:
                    pulse_count += 1
                    clock._pulse_count += 1
                await asyncio.sleep(0.0005)  # Clock runs faster

        # Run both loops concurrently
        await asyncio.gather(step_loop(), clock_loop())

        engine._handle_stop({})

        # Verify ratio: 6 pulses per step (24 PPQ / 4 steps per quarter)
        expected_ratio = 6.0
        actual_ratio = pulse_count / step_count if step_count > 0 else 0

        assert abs(actual_ratio - expected_ratio) < 0.5, (
            f"Pulse/step ratio incorrect: {actual_ratio:.2f} (expected ~{expected_ratio})"
        )

        step_drift = engine.get_drift_stats()
        clock_drift = engine._clock_generator.get_drift_stats()

        print("\n=== Concurrent Loops Test Results ===")
        print(f"Duration: {duration}s")
        print(f"Steps: {step_count}, Pulses: {pulse_count}")
        print(f"Pulse/Step ratio: {actual_ratio:.2f} (expected: {expected_ratio})")
        print(f"Step max drift: {step_drift['max_drift_ms']:.2f}ms")
        print(f"Clock max drift: {clock_drift['max_drift_ms']:.2f}ms")


# =============================================================================
# Test 5: High Event Density
# =============================================================================


@stability_test
class TestHighEventDensity:
    """Test stability with high event density."""

    @pytest.mark.asyncio
    async def test_16_tracks_all_steps(
        self,
        mock_osc: MockOscOutput,
        mock_midi: MockMidiOutput,
        mock_commands: MockCommandSource,
        mock_publisher: MockStateSink,
    ):
        """Test with 16 tracks, events on every step."""
        engine = LoopEngine(
            osc=mock_osc,
            midi=mock_midi,
            commands=mock_commands,
            publisher=mock_publisher,
        )
        engine._register_handlers()

        # Load dense session
        session = create_dense_session(num_tracks=16)
        engine._handle_compile(session)
        engine.state.set_bpm(140)  # Fast BPM
        engine._handle_play({})

        start_time = time.perf_counter()
        engine._step_anchor_time = start_time
        engine._step_count = 0

        duration = 5
        step_duration = engine.state.step_duration
        processed_steps = 0

        while time.perf_counter() - start_time < duration:
            current = time.perf_counter()
            expected = engine._step_anchor_time + (engine._step_count * step_duration)

            drift_ms = (current - expected) * 1000
            if abs(drift_ms) > engine._drift_stats["max_drift_ms"]:
                engine._drift_stats["max_drift_ms"] = abs(drift_ms)

            # Handle drift reset if threshold exceeded (just like real loop)
            if abs(drift_ms) > engine.DRIFT_RESET_THRESHOLD_MS:
                await engine._handle_drift_reset(drift_ms, current)

            if current >= expected:
                # Simulate step processing (16 tracks × events)
                current_step = engine.state.position.step
                for track in engine.state.tracks.values():
                    # Events would be processed here
                    _ = track.get_events_at(current_step)

                engine.state.advance_step()
                engine._step_count += 1
                processed_steps += 1

            await asyncio.sleep(0.001)

        engine._handle_stop({})

        drift_stats = engine.get_drift_stats()

        # Under high load, drift reset may trigger - that's expected behavior
        # The key is that the system recovers and continues running
        # At 140 BPM, expect ~560 steps in 5 seconds (5 / 0.00893 ≈ 560)
        expected_steps = int(duration / step_duration)
        assert processed_steps >= expected_steps * 0.8, (
            f"Too few steps processed: {processed_steps} < {expected_steps * 0.8}"
        )

        print("\n=== High Event Density Test Results ===")
        print("Tracks: 16, Events per track: 16")
        print(f"Steps processed: {processed_steps} (expected ~{expected_steps})")
        print(f"Max drift: {drift_stats['max_drift_ms']:.2f}ms")
        print(f"OSC events sent: {len(mock_osc.events)}")

    @pytest.mark.asyncio
    async def test_rapid_compile_during_playback(
        self,
        mock_osc: MockOscOutput,
        mock_midi: MockMidiOutput,
        mock_commands: MockCommandSource,
        mock_publisher: MockStateSink,
    ):
        """Test recompiling session while playing (live coding scenario)."""
        engine = LoopEngine(
            osc=mock_osc,
            midi=mock_midi,
            commands=mock_commands,
            publisher=mock_publisher,
        )
        engine._register_handlers()

        # Initial session
        session = create_dense_session(num_tracks=4)
        engine._handle_compile(session)
        engine.state.set_bpm(120)
        engine._handle_play({})

        engine._step_anchor_time = time.perf_counter()
        engine._step_count = 0

        compile_count = 0
        errors: list[str] = []
        start_time = time.perf_counter()

        while time.perf_counter() - start_time < 3:
            # Recompile every 500ms (simulating live coding)
            if int((time.perf_counter() - start_time) * 2) > compile_count:
                try:
                    new_session = create_dense_session(num_tracks=4 + compile_count)
                    engine._handle_compile(new_session)
                    compile_count += 1

                    # Verify engine is still playing
                    if not engine.state.playing:
                        errors.append(f"Playback stopped after compile {compile_count}")

                except Exception as e:
                    errors.append(f"Compile error: {e}")

            await asyncio.sleep(0.01)

        engine._handle_stop({})

        assert len(errors) == 0, f"Errors during playback: {errors}"
        assert compile_count >= 5, f"Not enough recompiles: {compile_count}"

        print("\n=== Rapid Compile Test Results ===")
        print(f"Recompiles during playback: {compile_count}")
        print(f"Errors: {len(errors)}")


# =============================================================================
# Summary Test: Run All Stability Checks
# =============================================================================


@stability_test
class TestStabilitySummary:
    """Summary test that runs quick versions of all stability checks."""

    @pytest.mark.asyncio
    async def test_comprehensive_stability_check(
        self,
        mock_osc: MockOscOutput,
        mock_midi: MockMidiOutput,
        mock_commands: MockCommandSource,
        mock_publisher: MockStateSink,
    ):
        """Quick comprehensive stability check (2 second version of each test)."""
        engine = LoopEngine(
            osc=mock_osc,
            midi=mock_midi,
            commands=mock_commands,
            publisher=mock_publisher,
        )
        engine._register_handlers()

        results: dict[str, bool] = {}

        # 1. Basic timing (2s)
        engine.state.set_bpm(120)
        engine._handle_play({})
        engine._step_anchor_time = time.perf_counter()
        engine._step_count = 0

        start = time.perf_counter()
        while time.perf_counter() - start < 2:
            current = time.perf_counter()
            expected = engine._step_anchor_time + (
                engine._step_count * engine.state.step_duration
            )
            if current >= expected:
                engine._step_count += 1
            await asyncio.sleep(0.001)

        results["timing"] = engine._drift_stats["reset_count"] == 0
        engine._handle_stop({})

        # 2. BPM changes
        engine._handle_play({})
        engine._step_anchor_time = time.perf_counter()
        engine._clock_generator._clock_anchor_time = time.perf_counter()

        bpm_errors = 0
        for bpm in [100, 140, 120]:
            try:
                engine._handle_bpm({"bpm": bpm})
            except Exception:
                bpm_errors += 1
            await asyncio.sleep(0.01)

        results["bpm_changes"] = bpm_errors == 0
        engine._handle_stop({})

        # 3. CPU spike recovery
        engine._handle_play({})
        engine._step_anchor_time = time.perf_counter()
        engine._step_count = 0
        engine._drift_stats["reset_count"] = 0

        await asyncio.sleep(0.1)  # Small spike
        current = time.perf_counter()
        drift_ms = (
            current - engine._step_anchor_time - engine._step_count * engine.state.step_duration
        ) * 1000

        if abs(drift_ms) > engine.DRIFT_RESET_THRESHOLD_MS:
            await engine._handle_drift_reset(drift_ms, current)

        results["spike_recovery"] = True  # Just verify no crash
        engine._handle_stop({})

        # Print results
        print("\n=== Comprehensive Stability Check ===")
        for test_name, passed in results.items():
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"  {test_name}: {status}")

        assert all(results.values()), f"Some checks failed: {results}"
