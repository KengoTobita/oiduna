"""
Tests for modulation application at runtime.

Tests the StepProcessor's ability to apply modulations
to OSC events using PARAM_SPECS.
"""

import pytest
from oiduna_core.models.modulation import PARAM_SPECS, Modulation, apply_modulation
from oiduna_core.models.sequence import Event, EventSequence
from oiduna_core.models.session import CompiledSession
from oiduna_core.models.step_buffer import StepBuffer
from oiduna_core.models.track import FxParams, Track, TrackFxParams, TrackMeta, TrackParams
from oiduna_loop.engine.step_processor import StepProcessor
from oiduna_loop.state.runtime_state import RuntimeState

from .mocks import MockOscOutput


@pytest.fixture
def osc_output() -> MockOscOutput:
    return MockOscOutput()


@pytest.fixture
def step_processor(osc_output: MockOscOutput) -> StepProcessor:
    return StepProcessor(osc_output)


def create_track_with_modulation(
    track_id: str,
    param_name: str,
    signal_values: tuple[float, ...],
) -> Track:
    """Helper to create a track with a single modulation."""
    return Track(
        meta=TrackMeta(track_id=track_id),
        params=TrackParams(s="test"),
        fx=FxParams(),
        modulations={
            param_name: Modulation(
                target_param=param_name,
                signal=StepBuffer(signal_values),
            )
        },
    )


class TestApplyModulation:
    """Tests for apply_modulation function."""

    def test_multiplicative_modulation(self) -> None:
        """Test multiplicative modulation (gain, speed, cutoff)."""
        spec = PARAM_SPECS["gain"]
        base = 1.0
        signal = 0.5  # +50%

        result = apply_modulation(base, signal, spec)

        # gain * (1 + signal) = 1.0 * 1.5 = 1.5
        assert result == pytest.approx(1.5)

    def test_additive_modulation(self) -> None:
        """Test additive modulation (resonance, room, shape)."""
        spec = PARAM_SPECS["resonance"]
        base = 0.5
        signal = 0.3

        result = apply_modulation(base, signal, spec)

        # base + signal * range = 0.5 + 0.3 * 1.0 = 0.8
        assert result == pytest.approx(0.8)

    def test_bipolar_modulation(self) -> None:
        """Test bipolar modulation (pan)."""
        spec = PARAM_SPECS["pan"]
        base = 0.5  # center
        signal = 0.5  # half right

        result = apply_modulation(base, signal, spec)

        # center + signal * half_range = 0.5 + 0.5 * 0.5 = 0.75
        assert result == pytest.approx(0.75)

    def test_modulation_clamped_to_range(self) -> None:
        """Test modulation result is clamped to valid range."""
        spec = PARAM_SPECS["gain"]
        base = 1.0
        signal = 2.0  # Would produce 3.0, but max is 2.0

        result = apply_modulation(base, signal, spec)

        assert result == 2.0  # Clamped to max

    def test_negative_modulation(self) -> None:
        """Test negative modulation signal."""
        spec = PARAM_SPECS["gain"]
        base = 1.0
        signal = -0.5  # -50%

        result = apply_modulation(base, signal, spec)

        # gain * (1 + signal) = 1.0 * 0.5 = 0.5
        assert result == pytest.approx(0.5)


class TestStepProcessorModulation:
    """Tests for StepProcessor modulation application."""

    def test_gain_modulation_applied(
        self, step_processor: StepProcessor, osc_output: MockOscOutput
    ) -> None:
        """Test gain modulation is applied to OSC event."""
        # Create track with gain modulation that varies by step
        signal = tuple(float(i) / 255.0 for i in range(256))  # 0.0 to 1.0
        track = create_track_with_modulation("test", "gain", signal)

        # Create session and state
        session = CompiledSession(
            tracks={"test": track},
            sequences={
                "test": EventSequence.from_events(
                    "test", [Event(step=0), Event(step=128)]
                )
            },
        )
        state = RuntimeState()
        state.load_session(session)
        state.position.step = 0

        # Process step 0
        output = step_processor.process_step_v2(state)

        assert len(output.osc_events) == 1
        # At step 0, signal = 0.0, so gain modulation = 1.0 * (1 + 0) = 1.0
        # With velocity 1.0, final_gain = 1.0 * 1.0 = 1.0
        assert output.osc_events[0].gain == pytest.approx(1.0)

        # Process step 128
        state.position.step = 128
        output = step_processor.process_step_v2(state)

        assert len(output.osc_events) == 1
        # At step 128, signal ≈ 0.5, so gain modulation = 1.0 * (1 + 0.5) = 1.5
        assert output.osc_events[0].gain == pytest.approx(1.5, rel=0.01)

    def test_pan_modulation_applied(
        self, step_processor: StepProcessor, osc_output: MockOscOutput
    ) -> None:
        """Test pan modulation is applied to OSC event."""
        # Pan modulation: alternating -0.4 and +0.4
        signal = tuple(0.4 if i % 2 == 0 else -0.4 for i in range(256))
        track = create_track_with_modulation("test", "pan", signal)

        session = CompiledSession(
            tracks={"test": track},
            sequences={
                "test": EventSequence.from_events(
                    "test", [Event(step=0), Event(step=1)]
                )
            },
        )
        state = RuntimeState()
        state.load_session(session)

        # Step 0: signal = 0.4
        state.position.step = 0
        output = step_processor.process_step_v2(state)
        # Pan is bipolar: 0.5 + 0.4 * 0.5 = 0.7
        assert output.osc_events[0].pan == pytest.approx(0.7)

        # Step 1: signal = -0.4
        state.position.step = 1
        output = step_processor.process_step_v2(state)
        # Pan is bipolar: 0.5 + (-0.4) * 0.5 = 0.3
        assert output.osc_events[0].pan == pytest.approx(0.3)

    def test_cutoff_modulation_applied(
        self, step_processor: StepProcessor, osc_output: MockOscOutput
    ) -> None:
        """Test cutoff modulation is applied to OSC event."""
        # Cutoff modulation: constant 0.5 = +50%
        signal = tuple(0.5 for _ in range(256))
        track = Track(
            meta=TrackMeta(track_id="test"),
            params=TrackParams(s="test"),
            fx=FxParams(cutoff=1000.0),  # Base cutoff
            modulations={
                "cutoff": Modulation(
                    target_param="cutoff",
                    signal=StepBuffer(signal),
                )
            },
        )

        session = CompiledSession(
            tracks={"test": track},
            sequences={
                "test": EventSequence.from_events("test", [Event(step=0)])
            },
        )
        state = RuntimeState()
        state.load_session(session)
        state.position.step = 0

        output = step_processor.process_step_v2(state)

        # Cutoff is multiplicative: 1000 * (1 + 0.5) = 1500
        assert output.osc_events[0].cutoff == pytest.approx(1500.0)

    def test_hierarchical_param_resolved(
        self, step_processor: StepProcessor, osc_output: MockOscOutput
    ) -> None:
        """Test hierarchical parameter names are resolved correctly."""
        signal = tuple(0.5 for _ in range(256))
        track = Track(
            meta=TrackMeta(track_id="test"),
            params=TrackParams(s="test"),
            fx=FxParams(cutoff=1000.0),
            modulations={
                "filter.cutoff": Modulation(
                    target_param="filter.cutoff",
                    signal=StepBuffer(signal),
                )
            },
        )

        session = CompiledSession(
            tracks={"test": track},
            sequences={
                "test": EventSequence.from_events("test", [Event(step=0)])
            },
        )
        state = RuntimeState()
        state.load_session(session)
        state.position.step = 0

        output = step_processor.process_step_v2(state)

        # "filter.cutoff" should resolve to "cutoff" parameter
        assert output.osc_events[0].cutoff == pytest.approx(1500.0)

    def test_multiple_modulations_applied(
        self, step_processor: StepProcessor, osc_output: MockOscOutput
    ) -> None:
        """Test multiple modulations are all applied."""
        track = Track(
            meta=TrackMeta(track_id="test"),
            params=TrackParams(s="test", gain=1.0, pan=0.5),
            fx=FxParams(cutoff=1000.0),
            modulations={
                "gain": Modulation(
                    target_param="gain",
                    signal=StepBuffer(tuple(0.5 for _ in range(256))),
                ),
                "pan": Modulation(
                    target_param="pan",
                    signal=StepBuffer(tuple(0.4 for _ in range(256))),
                ),
                "cutoff": Modulation(
                    target_param="cutoff",
                    signal=StepBuffer(tuple(0.2 for _ in range(256))),
                ),
            },
        )

        session = CompiledSession(
            tracks={"test": track},
            sequences={
                "test": EventSequence.from_events("test", [Event(step=0)])
            },
        )
        state = RuntimeState()
        state.load_session(session)
        state.position.step = 0

        output = step_processor.process_step_v2(state)

        event = output.osc_events[0]
        # Gain: 1.0 * (1 + 0.5) = 1.5 (then * velocity 1.0)
        assert event.gain == pytest.approx(1.5)
        # Pan: 0.5 + 0.4 * 0.5 = 0.7
        assert event.pan == pytest.approx(0.7)
        # Cutoff: 1000 * (1 + 0.2) = 1200
        assert event.cutoff == pytest.approx(1200.0)

    def test_no_modulation_uses_base_value(
        self, step_processor: StepProcessor, osc_output: MockOscOutput
    ) -> None:
        """Test that parameters without modulation use base values."""
        track = Track(
            meta=TrackMeta(track_id="test"),
            params=TrackParams(s="test", gain=0.8, pan=0.3),
            track_fx=TrackFxParams(cutoff=2000.0),
            modulations={},  # No modulations
        )

        session = CompiledSession(
            tracks={"test": track},
            sequences={
                "test": EventSequence.from_events("test", [Event(step=0)])
            },
        )
        state = RuntimeState()
        state.load_session(session)
        state.position.step = 0

        output = step_processor.process_step_v2(state)

        event = output.osc_events[0]
        # Base values preserved
        assert event.gain == pytest.approx(0.8)
        assert event.pan == pytest.approx(0.3)
        assert event.cutoff == pytest.approx(2000.0)
