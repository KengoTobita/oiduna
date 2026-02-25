"""
Performance tests for extension before_send_messages hooks.

Verifies that runtime hooks do not impact timing accuracy.
"""

import time
import statistics
from dataclasses import dataclass, replace

import pytest


@dataclass(frozen=True)
class MockScheduledMessage:
    """Mock ScheduledMessage for testing"""

    destination_id: str
    cycle: float
    step: int
    params: dict

    def replace(self, **kwargs):
        """Mimic dataclass replace"""
        return replace(self, **kwargs)


def mock_cps_injection_hook(messages, current_bpm, current_step):
    """
    Simulate SuperDirt extension's cps injection.

    This is the actual logic we'll use in production.
    """
    cps = current_bpm / 60.0 / 4.0

    return [
        msg.replace(params={**msg.params, "cps": cps})
        if msg.destination_id == "superdirt"
        else msg
        for msg in messages
    ]


class TestBeforeSendHooksPerformance:
    """Test suite for before_send_messages hook performance"""

    def test_hook_execution_time_single_message(self):
        """Verify hook execution time with 1 message"""
        messages = [
            MockScheduledMessage(
                destination_id="superdirt",
                cycle=0.0,
                step=0,
                params={"s": "bd", "gain": 0.8, "pan": 0.5, "speed": 1.0, "orbit": 0},
            )
        ]

        # Warm up
        for _ in range(100):
            mock_cps_injection_hook(messages, 120.0, 0)

        # Measure
        durations = []
        for _ in range(1000):
            start = time.perf_counter()
            result = mock_cps_injection_hook(messages, 120.0, 0)
            duration = time.perf_counter() - start
            durations.append(duration)

        # Statistics
        mean = statistics.mean(durations)
        p99 = sorted(durations)[int(len(durations) * 0.99)]

        print(f"\n1 message: mean={mean*1e6:.2f}μs, p99={p99*1e6:.2f}μs")

        # Assert p99 < 100μs (benchmark_plan.md requirement)
        assert p99 < 0.0001, f"p99 ({p99*1e6:.2f}μs) exceeds 100μs threshold"

    def test_hook_execution_time_multiple_messages(self):
        """Verify hook execution time with 4 messages"""
        messages = [
            MockScheduledMessage(
                destination_id="superdirt",
                cycle=0.0,
                step=0,
                params={
                    "s": f"sound{i}",
                    "gain": 0.8,
                    "pan": 0.5,
                    "speed": 1.0,
                    "orbit": i,
                    "delay": 0.1,
                    "room": 0.2,
                    "size": 0.5,
                    "cutoff": 1000,
                    "resonance": 0.3,
                },
            )
            for i in range(4)
        ]

        # Warm up
        for _ in range(100):
            mock_cps_injection_hook(messages, 120.0, 0)

        # Measure
        durations = []
        for _ in range(1000):
            start = time.perf_counter()
            result = mock_cps_injection_hook(messages, 120.0, 0)
            duration = time.perf_counter() - start
            durations.append(duration)

        # Statistics
        mean = statistics.mean(durations)
        p99 = sorted(durations)[int(len(durations) * 0.99)]

        print(f"\n4 messages: mean={mean*1e6:.2f}μs, p99={p99*1e6:.2f}μs")

        # Assert p99 < 100μs
        assert p99 < 0.0001, f"p99 ({p99*1e6:.2f}μs) exceeds 100μs threshold"

    def test_hook_execution_time_high_density(self):
        """Verify hook execution time with 10 messages (high density)"""
        messages = [
            MockScheduledMessage(
                destination_id="superdirt",
                cycle=0.0,
                step=0,
                params={
                    "s": f"sound{i}",
                    "gain": 0.8,
                    "pan": 0.5,
                    "speed": 1.0,
                    "orbit": i % 12,
                    "delay": 0.1,
                    "room": 0.2,
                    "size": 0.5,
                    "cutoff": 1000,
                    "resonance": 0.3,
                    "vowel": "a",
                    "accelerate": 0,
                    "shape": 0.5,
                    "hcutoff": 8000,
                    "hresonance": 0.2,
                    "bandf": 0.5,
                    "bandq": 0.5,
                    "crush": 0,
                    "coarse": 0,
                    "waveloss": 0,
                },
            )
            for i in range(10)
        ]

        # Warm up
        for _ in range(100):
            mock_cps_injection_hook(messages, 120.0, 0)

        # Measure
        durations = []
        for _ in range(1000):
            start = time.perf_counter()
            result = mock_cps_injection_hook(messages, 120.0, 0)
            duration = time.perf_counter() - start
            durations.append(duration)

        # Statistics
        mean = statistics.mean(durations)
        p99 = sorted(durations)[int(len(durations) * 0.99)]

        print(f"\n10 messages: mean={mean*1e6:.2f}μs, p99={p99*1e6:.2f}μs")

        # Assert p99 < 100μs
        assert p99 < 0.0001, f"p99 ({p99*1e6:.2f}μs) exceeds 100μs threshold"

    def test_hook_with_mixed_destinations(self):
        """Verify hook performance with mixed destinations (filtering logic)"""
        messages = [
            MockScheduledMessage(
                destination_id="superdirt" if i % 2 == 0 else "midi",
                cycle=0.0,
                step=0,
                params={"s": f"sound{i}", "gain": 0.8},
            )
            for i in range(8)
        ]

        # Measure
        durations = []
        for _ in range(1000):
            start = time.perf_counter()
            result = mock_cps_injection_hook(messages, 120.0, 0)
            duration = time.perf_counter() - start
            durations.append(duration)

        # Statistics
        mean = statistics.mean(durations)
        p99 = sorted(durations)[int(len(durations) * 0.99)]

        print(f"\nMixed destinations: mean={mean*1e6:.2f}μs, p99={p99*1e6:.2f}μs")

        # Assert p99 < 100μs
        assert p99 < 0.0001, f"p99 ({p99*1e6:.2f}μs) exceeds 100μs threshold"

        # Verify correctness: superdirt messages have cps, midi doesn't
        assert all(
            "cps" in msg.params if msg.destination_id == "superdirt" else "cps" not in msg.params
            for msg in result
        )

    def test_hook_correctness(self):
        """Verify hook produces correct output"""
        messages = [
            MockScheduledMessage(
                destination_id="superdirt",
                cycle=0.0,
                step=0,
                params={"s": "bd", "gain": 0.8},
            )
        ]

        result = mock_cps_injection_hook(messages, 120.0, 0)

        # Check cps was added
        assert len(result) == 1
        assert result[0].params["cps"] == 120.0 / 60.0 / 4.0
        assert result[0].params["s"] == "bd"
        assert result[0].params["gain"] == 0.8

    def test_hook_with_bpm_change(self):
        """Verify hook uses current BPM (not cached)"""
        messages = [
            MockScheduledMessage(
                destination_id="superdirt",
                cycle=0.0,
                step=0,
                params={"s": "bd"},
            )
        ]

        # BPM 120
        result1 = mock_cps_injection_hook(messages, 120.0, 0)
        assert result1[0].params["cps"] == 120.0 / 60.0 / 4.0

        # BPM 140
        result2 = mock_cps_injection_hook(messages, 140.0, 0)
        assert result2[0].params["cps"] == 140.0 / 60.0 / 4.0

        print("\nBPM change test: ✓ cps updates correctly")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
