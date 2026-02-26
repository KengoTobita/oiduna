"""Tests for StepProcessor Output IR (process_step_v2)."""

import pytest
from oiduna_core.ir.environment import Environment
from oiduna_core.modulation.modulation import Modulation
from oiduna_core.output.output import StepOutput
from oiduna_core.ir.sequence import Event, EventSequence
from oiduna_core.ir.session import CompiledSession
from oiduna_core.modulation.step_buffer import StepBuffer
from oiduna_core.ir.track import FxParams, Track, TrackFxParams, TrackMeta, TrackParams
from oiduna_core.ir.track_midi import TrackMidi
from oiduna_core.ir.mixer_line import MixerLine, MixerLineFx
from oiduna_core.ir.send import Send
from oiduna_loop.engine.step_processor import StepProcessor
from oiduna_loop.state import RuntimeState


class MockOscOutput:
    """Mock OSC output for testing."""

    def __init__(self) -> None:
        self.osc_events: list = []

    def connect(self) -> None:
        pass

    def disconnect(self) -> None:
        pass

    def send_osc_event(self, event) -> bool:
        self.osc_events.append(event)
        return True

    @property
    def is_connected(self) -> bool:
        return True


def create_test_track(
    track_id: str = "test",
    gain: float = 1.0,
    pan: float = 0.5,
    sound: str = "bd",
    modulations: dict | None = None,
    fx: FxParams | None = None,
    track_fx: TrackFxParams | None = None,
    sends: tuple[Send, ...] | None = None,
) -> Track:
    """Create a test track."""
    return Track(
        meta=TrackMeta(track_id=track_id),
        params=TrackParams(s=sound, gain=gain, pan=pan),
        fx=fx or FxParams(),
        track_fx=track_fx or TrackFxParams(),
        modulations=modulations or {},
        sends=sends or (),
    )


def create_test_event(
    step: int = 0,
    velocity: float = 1.0,
    note: int | None = None,
    gate: float = 1.0,
) -> Event:
    """Create a test event."""
    return Event(step=step, velocity=velocity, note=note, gate=gate)


def create_test_state(
    tracks: dict[str, Track] | None = None,
    sequences: dict[str, EventSequence] | None = None,
    tracks_midi: dict[str, TrackMidi] | None = None,
    mixer_lines: dict[str, MixerLine] | None = None,
    step: int = 0,
    bpm: float = 120.0,
) -> RuntimeState:
    """Create a test RuntimeState."""
    session = CompiledSession(
        environment=Environment(bpm=bpm),
        tracks=tracks or {},
        tracks_midi=tracks_midi or {},
        sequences=sequences or {},
        mixer_lines=mixer_lines or {},
    )
    state = RuntimeState()
    state.load_session(session)
    state.position.step = step
    state.playback_state = state.playback_state.PLAYING
    return state


class TestProcessStepV2Basic:
    """Basic tests for process_step_v2."""

    def test_returns_step_output(self) -> None:
        """Verify process_step_v2 returns StepOutput."""
        processor = StepProcessor(MockOscOutput())
        state = create_test_state()

        output = processor.process_step_v2(state)

        assert isinstance(output, StepOutput)

    def test_step_matches_position(self) -> None:
        """Verify output step matches state position."""
        processor = StepProcessor(MockOscOutput())
        state = create_test_state(step=48)

        output = processor.process_step_v2(state)

        assert output.step == 48

    def test_empty_state_returns_empty_output(self) -> None:
        """Verify empty state returns empty StepOutput."""
        processor = StepProcessor(MockOscOutput())
        state = create_test_state()

        output = processor.process_step_v2(state)

        assert output.is_empty
        assert output.event_count == 0


class TestOscEventGeneration:
    """Tests for OscEvent generation."""

    def test_basic_osc_event(self) -> None:
        """Test basic OscEvent generation."""
        track = create_test_track(track_id="kick", sound="super808", gain=0.8)
        event = create_test_event(step=0, velocity=1.0)
        sequence = EventSequence.from_events("kick", [event])

        processor = StepProcessor(MockOscOutput())
        state = create_test_state(
            tracks={"kick": track},
            sequences={"kick": sequence},
            step=0,
        )

        output = processor.process_step_v2(state)

        assert len(output.osc_events) == 1
        osc = output.osc_events[0]
        assert osc.sound == "super808"
        assert osc.gain == pytest.approx(0.8)
        # Check params dict (orbit is now in params, not explicit field)
        assert osc.params["orbit"] == 0
        assert osc.params["cps"] == 0.5  # BPM 120 / 60 / 4

    def test_gain_includes_velocity(self) -> None:
        """Verify gain = base_gain * velocity."""
        track = create_test_track(gain=0.8)
        event = create_test_event(step=0, velocity=0.5)
        sequence = EventSequence.from_events("test", [event])

        processor = StepProcessor(MockOscOutput())
        state = create_test_state(
            tracks={"test": track},
            sequences={"test": sequence},
        )

        output = processor.process_step_v2(state)

        assert output.osc_events[0].gain == pytest.approx(0.4)

    def test_gain_with_modulation(self) -> None:
        """Verify modulation is applied to gain."""
        # Create modulation with +0.5 at step 0
        mod_values = [0.5] + [0.0] * 255
        modulation = Modulation(
            target_param="gain",
            signal=StepBuffer.from_sequence(mod_values),
        )
        track = create_test_track(
            gain=1.0,
            modulations={"gain": modulation},
        )
        event = create_test_event(step=0, velocity=1.0)
        sequence = EventSequence.from_events("test", [event])

        processor = StepProcessor(MockOscOutput())
        state = create_test_state(
            tracks={"test": track},
            sequences={"test": sequence},
            step=0,
        )

        output = processor.process_step_v2(state)

        # gain = 1.0 * 1.0 * (1 + 0.5) = 1.5
        assert output.osc_events[0].gain == pytest.approx(1.5)

    def test_pan_with_modulation(self) -> None:
        """Verify modulation is applied to pan."""
        # Create modulation with +0.5 at step 0
        mod_values = [0.5] + [0.0] * 255
        modulation = Modulation(
            target_param="pan",
            signal=StepBuffer.from_sequence(mod_values),
        )
        track = create_test_track(
            pan=0.5,
            modulations={"pan": modulation},
        )
        event = create_test_event(step=0)
        sequence = EventSequence.from_events("test", [event])

        processor = StepProcessor(MockOscOutput())
        state = create_test_state(
            tracks={"test": track},
            sequences={"test": sequence},
            step=0,
        )

        output = processor.process_step_v2(state)

        # pan = 0.5 + 0.5 * 0.5 = 0.75
        assert output.osc_events[0].pan == pytest.approx(0.75)

    def test_sustain_converted_to_seconds(self) -> None:
        """Verify gate is converted to sustain in seconds."""
        track = create_test_track()
        event = create_test_event(step=0, gate=1.0)
        sequence = EventSequence.from_events("test", [event])

        processor = StepProcessor(MockOscOutput())
        state = create_test_state(
            tracks={"test": track},
            sequences={"test": sequence},
            bpm=120.0,  # cps = 0.5
        )

        output = processor.process_step_v2(state)

        # sustain = gate / (cps * 16) = 1.0 / (0.5 * 16) = 0.125
        assert output.osc_events[0].sustain == pytest.approx(0.125)

    def test_midinote_included_when_present(self) -> None:
        """Verify midinote is included when event has note."""
        track = create_test_track()
        event = create_test_event(step=0, note=60)
        sequence = EventSequence.from_events("test", [event])

        processor = StepProcessor(MockOscOutput())
        state = create_test_state(
            tracks={"test": track},
            sequences={"test": sequence},
        )

        output = processor.process_step_v2(state)

        assert output.osc_events[0].midinote == 60

    def test_effects_included(self) -> None:
        """Verify FX params are included in OscEvent."""
        # Tone-shaping effects from TrackFxParams
        track_fx = TrackFxParams(cutoff=1500.0)
        # Spatial effects from FxParams (reverb, delay)
        fx = FxParams(room=0.3, delay_send=0.2)
        track = create_test_track(fx=fx, track_fx=track_fx)
        event = create_test_event(step=0)
        sequence = EventSequence.from_events("test", [event])

        processor = StepProcessor(MockOscOutput())
        state = create_test_state(
            tracks={"test": track},
            sequences={"test": sequence},
        )

        output = processor.process_step_v2(state)

        osc = output.osc_events[0]
        assert osc.cutoff == 1500.0
        assert osc.room == 0.3
        assert osc.delay_send == 0.2

    def test_multiple_events_same_step(self) -> None:
        """Test multiple events at the same step."""
        track = create_test_track()
        events = [
            create_test_event(step=0, velocity=0.8),
            create_test_event(step=0, velocity=0.6),
        ]
        sequence = EventSequence.from_events("test", events)

        processor = StepProcessor(MockOscOutput())
        state = create_test_state(
            tracks={"test": track},
            sequences={"test": sequence},
        )

        output = processor.process_step_v2(state)

        assert len(output.osc_events) == 2


class TestMidiNoteEventGeneration:
    """Tests for MidiNoteEvent generation."""

    def test_basic_midi_note(self) -> None:
        """Test basic MidiNoteEvent generation."""
        track_midi = TrackMidi(track_id="synth", channel=0, velocity=127)
        event = create_test_event(step=0, note=60, velocity=1.0)
        sequence = EventSequence.from_events("synth", [event])

        processor = StepProcessor(MockOscOutput())
        state = create_test_state(
            tracks_midi={"synth": track_midi},
            sequences={"synth": sequence},
        )

        output = processor.process_step_v2(state)

        assert len(output.midi_notes) == 1
        note = output.midi_notes[0]
        assert note.channel == 0
        assert note.note == 60
        assert note.velocity == 127

    def test_transpose_applied(self) -> None:
        """Verify transpose is applied to note."""
        track_midi = TrackMidi(track_id="synth", channel=0, velocity=127, transpose=12)
        event = create_test_event(step=0, note=60)
        sequence = EventSequence.from_events("synth", [event])

        processor = StepProcessor(MockOscOutput())
        state = create_test_state(
            tracks_midi={"synth": track_midi},
            sequences={"synth": sequence},
        )

        output = processor.process_step_v2(state)

        assert output.midi_notes[0].note == 72  # 60 + 12

    def test_transpose_clamped_to_midi_range(self) -> None:
        """Verify transposed note is clamped to 0-127."""
        track_midi = TrackMidi(track_id="synth", channel=0, velocity=127, transpose=100)
        event = create_test_event(step=0, note=60)
        sequence = EventSequence.from_events("synth", [event])

        processor = StepProcessor(MockOscOutput())
        state = create_test_state(
            tracks_midi={"synth": track_midi},
            sequences={"synth": sequence},
        )

        output = processor.process_step_v2(state)

        assert output.midi_notes[0].note == 127  # Clamped

    def test_velocity_scaled(self) -> None:
        """Verify velocity is scaled by event velocity."""
        track_midi = TrackMidi(track_id="synth", channel=0, velocity=100)
        event = create_test_event(step=0, note=60, velocity=0.5)
        sequence = EventSequence.from_events("synth", [event])

        processor = StepProcessor(MockOscOutput())
        state = create_test_state(
            tracks_midi={"synth": track_midi},
            sequences={"synth": sequence},
        )

        output = processor.process_step_v2(state)

        assert output.midi_notes[0].velocity == 50  # 100 * 0.5

    def test_no_note_returns_no_event(self) -> None:
        """Verify no MidiNoteEvent when event has no note."""
        track_midi = TrackMidi(track_id="synth", channel=0, velocity=127)
        event = create_test_event(step=0, note=None)
        sequence = EventSequence.from_events("synth", [event])

        processor = StepProcessor(MockOscOutput())
        state = create_test_state(
            tracks_midi={"synth": track_midi},
            sequences={"synth": sequence},
        )

        output = processor.process_step_v2(state)

        assert len(output.midi_notes) == 0

    def test_duration_calculated_from_gate(self) -> None:
        """Verify duration is calculated from gate."""
        track_midi = TrackMidi(track_id="synth", channel=0, velocity=127)
        event = create_test_event(step=0, note=60, gate=2.0)
        sequence = EventSequence.from_events("synth", [event])

        processor = StepProcessor(MockOscOutput())
        state = create_test_state(
            tracks_midi={"synth": track_midi},
            sequences={"synth": sequence},
            bpm=120.0,  # cps = 0.5
        )

        output = processor.process_step_v2(state)

        # duration_ms = (gate / (cps * 16)) * 1000 = (2.0 / 8) * 1000 = 250
        assert output.midi_notes[0].duration_ms == 250


class TestMidiCCEventGeneration:
    """Tests for MidiCCEvent generation."""

    def test_cc_from_modulation(self) -> None:
        """Test MidiCCEvent generation from modulation."""
        # Create modulation with 0.0 at step 0 (center = 64)
        mod_values = [0.0] * 256
        modulation = Modulation(
            target_param="cc",
            signal=StepBuffer.from_sequence(mod_values),
        )
        track_midi = TrackMidi(
            track_id="synth",
            channel=0,
            velocity=127,
            cc_modulations={74: modulation},  # CC 74 = cutoff
        )

        processor = StepProcessor(MockOscOutput())
        state = create_test_state(
            tracks_midi={"synth": track_midi},
            step=0,
        )

        output = processor.process_step_v2(state)

        assert len(output.midi_ccs) == 1
        cc = output.midi_ccs[0]
        assert cc.channel == 0
        assert cc.cc == 74
        assert cc.value == 63  # (0.0 + 1.0) / 2 * 127 ≈ 63

    def test_cc_value_from_signal(self) -> None:
        """Verify CC value is converted from signal."""
        # Signal = 1.0 → CC = 127
        mod_values = [1.0] * 256
        modulation = Modulation(
            target_param="cc",
            signal=StepBuffer.from_sequence(mod_values),
        )
        track_midi = TrackMidi(
            track_id="synth",
            channel=0,
            velocity=127,
            cc_modulations={1: modulation},  # CC 1 = mod wheel
        )

        processor = StepProcessor(MockOscOutput())
        state = create_test_state(
            tracks_midi={"synth": track_midi},
            step=0,
        )

        output = processor.process_step_v2(state)

        assert output.midi_ccs[0].value == 127

    def test_cc_value_negative_signal(self) -> None:
        """Verify negative signal converts to low CC value."""
        # Signal = -1.0 → CC = 0
        mod_values = [-1.0] * 256
        modulation = Modulation(
            target_param="cc",
            signal=StepBuffer.from_sequence(mod_values),
        )
        track_midi = TrackMidi(
            track_id="synth",
            channel=0,
            velocity=127,
            cc_modulations={1: modulation},
        )

        processor = StepProcessor(MockOscOutput())
        state = create_test_state(
            tracks_midi={"synth": track_midi},
            step=0,
        )

        output = processor.process_step_v2(state)

        assert output.midi_ccs[0].value == 0


class TestMixedOutput:
    """Tests for mixed OSC and MIDI output."""

    def test_osc_and_midi_together(self) -> None:
        """Test StepOutput with both OSC and MIDI events."""
        # SuperDirt track
        track = create_test_track(track_id="kick")
        event_osc = create_test_event(step=0)
        seq_osc = EventSequence.from_events("kick", [event_osc])

        # MIDI track
        track_midi = TrackMidi(track_id="synth", channel=0, velocity=127)
        event_midi = create_test_event(step=0, note=60)
        seq_midi = EventSequence.from_events("synth", [event_midi])

        processor = StepProcessor(MockOscOutput())
        state = create_test_state(
            tracks={"kick": track},
            tracks_midi={"synth": track_midi},
            sequences={"kick": seq_osc, "synth": seq_midi},
        )

        output = processor.process_step_v2(state)

        assert len(output.osc_events) == 1
        assert len(output.midi_notes) == 1
        assert output.event_count == 2


class TestToOscArgs:
    """Tests for OscEvent.to_osc_args() integration."""

    def test_osc_args_format(self) -> None:
        """Verify to_osc_args produces correct format."""
        track = create_test_track(sound="super808", gain=0.8)
        event = create_test_event(step=0)
        sequence = EventSequence.from_events("test", [event])

        processor = StepProcessor(MockOscOutput())
        state = create_test_state(
            tracks={"test": track},
            sequences={"test": sequence},
        )

        output = processor.process_step_v2(state)
        args = output.osc_events[0].to_osc_args()

        # Should be [key, value, key, value, ...]
        assert len(args) % 2 == 0
        assert "s" in args
        assert args[args.index("s") + 1] == "super808"

    def test_delay_send_uses_correct_osc_name(self) -> None:
        """Verify delay_send is sent as 'delaySend' in OSC args."""
        fx = FxParams(delay_send=0.5)
        track = create_test_track(fx=fx)
        event = create_test_event(step=0)
        sequence = EventSequence.from_events("test", [event])

        processor = StepProcessor(MockOscOutput())
        state = create_test_state(
            tracks={"test": track},
            sequences={"test": sequence},
        )

        output = processor.process_step_v2(state)
        args = output.osc_events[0].to_osc_args()

        # Should use "delaySend" not "delay"
        assert "delaySend" in args
        assert "delay" not in args
        assert args[args.index("delaySend") + 1] == 0.5


class TestTremoloPhaser:
    """Tests for tremolo/phaser parameters from TrackFxParams."""

    def test_tremolo_params_in_osc_event(self) -> None:
        """Verify tremolo params from TrackFxParams are included."""
        track_fx = TrackFxParams(tremolo_rate=4.0, tremolo_depth=0.5)
        track = create_test_track(track_fx=track_fx)
        event = create_test_event(step=0)
        sequence = EventSequence.from_events("test", [event])

        processor = StepProcessor(MockOscOutput())
        state = create_test_state(
            tracks={"test": track},
            sequences={"test": sequence},
        )

        output = processor.process_step_v2(state)
        osc = output.osc_events[0]

        assert osc.tremolorate == 4.0
        assert osc.tremolodepth == 0.5

    def test_phaser_params_in_osc_event(self) -> None:
        """Verify phaser params from TrackFxParams are included."""
        track_fx = TrackFxParams(phaser_rate=2.0, phaser_depth=0.3)
        track = create_test_track(track_fx=track_fx)
        event = create_test_event(step=0)
        sequence = EventSequence.from_events("test", [event])

        processor = StepProcessor(MockOscOutput())
        state = create_test_state(
            tracks={"test": track},
            sequences={"test": sequence},
        )

        output = processor.process_step_v2(state)
        osc = output.osc_events[0]

        assert osc.phaserrate == 2.0
        assert osc.phaserdepth == 0.3


class TestLeslieFromMixerLine:
    """Tests for Leslie parameters from MixerLine."""

    def test_leslie_from_mixer_line(self) -> None:
        """Verify Leslie params are extracted from MixerLine."""
        track = create_test_track(track_id="organ")
        event = create_test_event(step=0)
        sequence = EventSequence.from_events("organ", [event])

        # Create MixerLine with Leslie enabled
        mixer_line = MixerLine(
            name="keys",
            include=("organ",),
            fx=MixerLineFx(leslie_rate=5.0, leslie_size=0.7),
        )

        processor = StepProcessor(MockOscOutput())
        state = create_test_state(
            tracks={"organ": track},
            sequences={"organ": sequence},
            mixer_lines={"keys": mixer_line},
        )

        output = processor.process_step_v2(state)
        osc = output.osc_events[0]

        assert osc.leslie == 1.0  # On
        assert osc.lrate == 5.0
        assert osc.lsize == 0.7

    def test_no_leslie_when_rate_zero(self) -> None:
        """Verify Leslie is None when rate is 0."""
        track = create_test_track(track_id="organ")
        event = create_test_event(step=0)
        sequence = EventSequence.from_events("organ", [event])

        # MixerLine with Leslie rate = 0 (off)
        mixer_line = MixerLine(
            name="keys",
            include=("organ",),
            fx=MixerLineFx(leslie_rate=0.0, leslie_size=0.5),
        )

        processor = StepProcessor(MockOscOutput())
        state = create_test_state(
            tracks={"organ": track},
            sequences={"organ": sequence},
            mixer_lines={"keys": mixer_line},
        )

        output = processor.process_step_v2(state)
        osc = output.osc_events[0]

        assert osc.leslie is None
        assert osc.lrate is None
        assert osc.lsize is None

    def test_no_leslie_when_track_not_in_mixer_line(self) -> None:
        """Verify Leslie is None when track is not in any MixerLine."""
        track = create_test_track(track_id="drums")
        event = create_test_event(step=0)
        sequence = EventSequence.from_events("drums", [event])

        # MixerLine does not include "drums"
        mixer_line = MixerLine(
            name="keys",
            include=("organ",),
            fx=MixerLineFx(leslie_rate=5.0, leslie_size=0.7),
        )

        processor = StepProcessor(MockOscOutput())
        state = create_test_state(
            tracks={"drums": track},
            sequences={"drums": sequence},
            mixer_lines={"keys": mixer_line},
        )

        output = processor.process_step_v2(state)
        osc = output.osc_events[0]

        assert osc.leslie is None


class TestSpatialFxFromMixerLine:
    """Tests for spatial effects (reverb, delay) from MixerLine."""

    def test_reverb_from_mixer_line(self) -> None:
        """Verify reverb params are extracted from MixerLine.fx."""
        track = create_test_track(track_id="pad")
        event = create_test_event(step=0)
        sequence = EventSequence.from_events("pad", [event])

        mixer_line = MixerLine(
            name="pads",
            include=("pad",),
            fx=MixerLineFx(reverb_room=0.8, reverb_size=0.9, reverb_dry=0.3),
        )

        processor = StepProcessor(MockOscOutput())
        state = create_test_state(
            tracks={"pad": track},
            sequences={"pad": sequence},
            mixer_lines={"pads": mixer_line},
        )

        output = processor.process_step_v2(state)
        osc = output.osc_events[0]

        assert osc.room == 0.8
        assert osc.size == 0.9
        assert osc.dry == 0.3

    def test_delay_from_mixer_line(self) -> None:
        """Verify delay params are extracted from MixerLine.fx."""
        track = create_test_track(track_id="synth")
        event = create_test_event(step=0)
        sequence = EventSequence.from_events("synth", [event])

        mixer_line = MixerLine(
            name="synths",
            include=("synth",),
            fx=MixerLineFx(delay_send=0.6, delay_time=0.25, delay_feedback=0.4),
        )

        processor = StepProcessor(MockOscOutput())
        state = create_test_state(
            tracks={"synth": track},
            sequences={"synth": sequence},
            mixer_lines={"synths": mixer_line},
        )

        output = processor.process_step_v2(state)
        osc = output.osc_events[0]

        assert osc.delay_send == 0.6
        assert osc.delaytime == 0.25
        assert osc.delayfeedback == 0.4

    def test_mixer_line_fx_overrides_track_fx(self) -> None:
        """Verify MixerLine.fx takes priority over Track.fx for spatial effects."""
        # Track has reverb set
        fx = FxParams(room=0.2, delay_send=0.1)
        track = create_test_track(track_id="lead", fx=fx)
        event = create_test_event(step=0)
        sequence = EventSequence.from_events("lead", [event])

        # MixerLine has different reverb values
        mixer_line = MixerLine(
            name="leads",
            include=("lead",),
            fx=MixerLineFx(reverb_room=0.7, delay_send=0.5),
        )

        processor = StepProcessor(MockOscOutput())
        state = create_test_state(
            tracks={"lead": track},
            sequences={"lead": sequence},
            mixer_lines={"leads": mixer_line},
        )

        output = processor.process_step_v2(state)
        osc = output.osc_events[0]

        # Should use MixerLine values, not Track.fx
        assert osc.room == 0.7
        assert osc.delay_send == 0.5

    def test_fallback_to_track_fx_when_no_mixer_line(self) -> None:
        """Verify spatial effects fallback to Track.fx when no MixerLine."""
        fx = FxParams(room=0.4, delay_send=0.3)
        track = create_test_track(track_id="bass", fx=fx)
        event = create_test_event(step=0)
        sequence = EventSequence.from_events("bass", [event])

        # No MixerLine for this track
        processor = StepProcessor(MockOscOutput())
        state = create_test_state(
            tracks={"bass": track},
            sequences={"bass": sequence},
            mixer_lines={},  # Empty
        )

        output = processor.process_step_v2(state)
        osc = output.osc_events[0]

        # Should fallback to Track.fx values
        assert osc.room == 0.4
        assert osc.delay_send == 0.3

    def test_partial_mixer_line_fx_with_track_fx_fallback(self) -> None:
        """Verify partial MixerLine.fx values fallback to Track.fx for None values."""
        # Track has full FxParams
        fx = FxParams(room=0.3, size=0.5, dry=0.2, delay_send=0.4, delay_time=0.3, delay_feedback=0.5)
        track = create_test_track(track_id="keys", fx=fx)
        event = create_test_event(step=0)
        sequence = EventSequence.from_events("keys", [event])

        # MixerLine only sets room, leaves delay at default
        mixer_line = MixerLine(
            name="keyboards",
            include=("keys",),
            fx=MixerLineFx(reverb_room=0.9),  # Only room set
        )

        processor = StepProcessor(MockOscOutput())
        state = create_test_state(
            tracks={"keys": track},
            sequences={"keys": sequence},
            mixer_lines={"keyboards": mixer_line},
        )

        output = processor.process_step_v2(state)
        osc = output.osc_events[0]

        # Room from MixerLine
        assert osc.room == 0.9
        # Delay from MixerLine (default value 0.0, not Track.fx fallback)
        # When MixerLine exists, all values come from MixerLine.fx
        assert osc.delay_send == 0.0


class TestTrackSends:
    """Tests for Track.sends generating additional OscEvents."""

    def test_send_generates_additional_osc_event(self) -> None:
        """Verify Track.sends generates additional OscEvent to target MixerLine."""
        # Track with a send to "reverb_bus"
        send = Send(target="reverb_bus", amount=0.5)
        track = create_test_track(track_id="vocal", gain=1.0, sends=(send,))
        event = create_test_event(step=0, velocity=1.0)
        sequence = EventSequence.from_events("vocal", [event])

        # Main MixerLine for the track
        main_ml = MixerLine(name="vocals", include=("vocal",))

        # Target MixerLine for sends
        reverb_ml = MixerLine(
            name="reverb_bus",
            include=(),  # Dedicated bus, no direct tracks
            fx=MixerLineFx(reverb_room=0.9, reverb_size=0.8),
        )

        processor = StepProcessor(MockOscOutput())
        state = create_test_state(
            tracks={"vocal": track},
            sequences={"vocal": sequence},
            mixer_lines={"vocals": main_ml, "reverb_bus": reverb_ml},
        )

        output = processor.process_step_v2(state)

        # Should have 2 events: main + send
        assert len(output.osc_events) == 2

        # First event is main output
        main_event = output.osc_events[0]
        assert main_event.gain == pytest.approx(1.0)

        # Second event is send output with reduced gain
        send_event = output.osc_events[1]
        assert send_event.gain == pytest.approx(0.5)  # 1.0 * 0.5
        assert send_event.room == 0.9  # From reverb_bus MixerLine
        assert send_event.size == 0.8

    def test_send_uses_target_mixer_line_orbit(self) -> None:
        """Verify send event uses target MixerLine's orbit."""
        send = Send(target="fx_bus", amount=0.6)
        track = create_test_track(track_id="guitar", sends=(send,))
        event = create_test_event(step=0)
        sequence = EventSequence.from_events("guitar", [event])

        main_ml = MixerLine(name="guitars", include=("guitar",))
        fx_ml = MixerLine(name="fx_bus", include=())

        processor = StepProcessor(MockOscOutput())
        state = create_test_state(
            tracks={"guitar": track},
            sequences={"guitar": sequence},
            mixer_lines={"guitars": main_ml, "fx_bus": fx_ml},
        )

        output = processor.process_step_v2(state)

        # Main event uses guitars orbit (0)
        # Send event uses fx_bus orbit (1)
        main_event = output.osc_events[0]
        send_event = output.osc_events[1]

        assert main_event.orbit == 0  # First MixerLine
        assert send_event.orbit == 1  # Second MixerLine

    def test_multiple_sends(self) -> None:
        """Verify multiple sends generate multiple additional events."""
        sends = (
            Send(target="reverb_bus", amount=0.4),
            Send(target="delay_bus", amount=0.3),
        )
        track = create_test_track(track_id="synth", gain=0.8, sends=sends)
        event = create_test_event(step=0, velocity=1.0)
        sequence = EventSequence.from_events("synth", [event])

        main_ml = MixerLine(name="synths", include=("synth",))
        reverb_ml = MixerLine(name="reverb_bus", include=(), fx=MixerLineFx(reverb_room=0.7))
        delay_ml = MixerLine(name="delay_bus", include=(), fx=MixerLineFx(delay_send=0.8))

        processor = StepProcessor(MockOscOutput())
        state = create_test_state(
            tracks={"synth": track},
            sequences={"synth": sequence},
            mixer_lines={"synths": main_ml, "reverb_bus": reverb_ml, "delay_bus": delay_ml},
        )

        output = processor.process_step_v2(state)

        # Should have 3 events: main + 2 sends
        assert len(output.osc_events) == 3

        main_event = output.osc_events[0]
        reverb_send = output.osc_events[1]
        delay_send = output.osc_events[2]

        assert main_event.gain == pytest.approx(0.8)
        assert reverb_send.gain == pytest.approx(0.32)  # 0.8 * 0.4
        assert delay_send.gain == pytest.approx(0.24)  # 0.8 * 0.3

    def test_send_to_same_mixer_line_skipped(self) -> None:
        """Verify send to same MixerLine is skipped (no duplicate)."""
        # Send targets the same MixerLine the track belongs to
        send = Send(target="vocals", amount=0.5)
        track = create_test_track(track_id="vocal", sends=(send,))
        event = create_test_event(step=0)
        sequence = EventSequence.from_events("vocal", [event])

        vocals_ml = MixerLine(name="vocals", include=("vocal",))

        processor = StepProcessor(MockOscOutput())
        state = create_test_state(
            tracks={"vocal": track},
            sequences={"vocal": sequence},
            mixer_lines={"vocals": vocals_ml},
        )

        output = processor.process_step_v2(state)

        # Should only have 1 event (main), send to same bus is skipped
        assert len(output.osc_events) == 1

    def test_send_to_nonexistent_mixer_line_skipped(self) -> None:
        """Verify send to nonexistent MixerLine is skipped."""
        send = Send(target="nonexistent_bus", amount=0.5)
        track = create_test_track(track_id="lead", sends=(send,))
        event = create_test_event(step=0)
        sequence = EventSequence.from_events("lead", [event])

        main_ml = MixerLine(name="leads", include=("lead",))

        processor = StepProcessor(MockOscOutput())
        state = create_test_state(
            tracks={"lead": track},
            sequences={"lead": sequence},
            mixer_lines={"leads": main_ml},  # No "nonexistent_bus"
        )

        output = processor.process_step_v2(state)

        # Should only have 1 event (main), invalid send is skipped
        assert len(output.osc_events) == 1

    def test_send_with_velocity(self) -> None:
        """Verify send gain includes event velocity."""
        send = Send(target="fx_bus", amount=0.5)
        track = create_test_track(track_id="snare", gain=1.0, sends=(send,))
        event = create_test_event(step=0, velocity=0.8)
        sequence = EventSequence.from_events("snare", [event])

        main_ml = MixerLine(name="drums", include=("snare",))
        fx_ml = MixerLine(name="fx_bus", include=())

        processor = StepProcessor(MockOscOutput())
        state = create_test_state(
            tracks={"snare": track},
            sequences={"snare": sequence},
            mixer_lines={"drums": main_ml, "fx_bus": fx_ml},
        )

        output = processor.process_step_v2(state)

        main_event = output.osc_events[0]
        send_event = output.osc_events[1]

        # Main: 1.0 * 0.8 = 0.8
        assert main_event.gain == pytest.approx(0.8)
        # Send: 1.0 * 0.8 * 0.5 = 0.4
        assert send_event.gain == pytest.approx(0.4)
