"""
Step Processor

Handles step processing logic, separated from LoopEngine.
Martin Fowler: Extract Class, Single Responsibility Principle.

v5: Uses RuntimeState with CompiledSession models.
Uses Output IR (Layer 3) via process_step_v2().
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, NamedTuple, cast

from oiduna_core.ir.mixer_line import MixerLine
from oiduna_core.modulation import PARAM_SPECS, apply_modulation
from oiduna_core.output.output import (
    MidiAftertouchEvent,
    MidiCCEvent,
    MidiNoteEvent,
    MidiPitchBendEvent,
    OscEvent,
    StepOutput,
)
from oiduna_core.ir.track import Track
from oiduna_core.ir.track_midi import TrackMidi

from ..protocols import OscOutput
from ..state import STEPS_PER_BAR

if TYPE_CHECKING:
    from oiduna_core.ir.sequence import Event

    from ..state import RuntimeState


class SpatialFx(NamedTuple):
    """Spatial effects parameters (reverb, delay, leslie)."""

    room: float | None
    size: float | None
    dry: float | None
    delay_send: float | None
    delay_time: float | None
    delay_feedback: float | None
    leslie: float | None
    lrate: float | None
    lsize: float | None

logger = logging.getLogger(__name__)


class MidiNote(NamedTuple):
    """
    MIDI note data for scheduling.

    Martin Fowler: Replace Primitive with Object.
    Using NamedTuple instead of raw tuple for type safety and clarity.
    """

    track_id: str
    channel: int
    note: int
    velocity: int
    gate: float


class StepProcessor:
    """
    Processes step events for OSC/MIDI output.

    Single responsibility: Convert track events to output events.
    v5: Works with RuntimeState and CompiledSession models.

    Uses process_step_v2() which returns StepOutput (Output IR).
    Caller is responsible for sending events.
    """

    def __init__(self, osc: OscOutput):
        """
        Initialize step processor.

        Args:
            osc: OSC output (OscSender or mock)
        """
        self._osc = osc

    def _find_mixer_line_for_track(
        self,
        track_id: str,
        mixer_lines: dict[str, MixerLine] | None,
    ) -> MixerLine | None:
        """
        Find the MixerLine that includes this track.

        Args:
            track_id: Track ID to search for
            mixer_lines: Dictionary of MixerLines

        Returns:
            MixerLine that includes the track, or None
        """
        if not mixer_lines:
            return None
        for ml in mixer_lines.values():
            if track_id in ml.include:
                return ml
        return None

    def _get_spatial_fx(
        self,
        track: Track,
        mixer_line: MixerLine | None,
        modulated: dict[str, float],
    ) -> SpatialFx:
        """
        Get spatial effects from MixerLine or Track.fx (fallback).

        v5 design: Spatial effects (reverb, delay, leslie) should come from
        MixerLine.fx. Falls back to Track.fx for backwards compatibility
        when no MixerLine is defined.

        Args:
            track: Track definition
            mixer_line: MixerLine the track belongs to (can be None)
            modulated: Modulated parameter values

        Returns:
            SpatialFx tuple with all spatial effect parameters
        """
        if mixer_line:
            ml_fx = mixer_line.fx
            # Get spatial effects from MixerLine
            room = modulated.get("room", ml_fx.reverb_room)
            size = modulated.get("size", ml_fx.reverb_size)
            dry = modulated.get("dry", ml_fx.reverb_dry)
            delay_send = modulated.get("delay_send", ml_fx.delay_send)
            delay_time = modulated.get("delay_time", ml_fx.delay_time)
            delay_feedback = modulated.get("delay_feedback", ml_fx.delay_feedback)

            # Leslie from MixerLine
            leslie: float | None = None
            lrate: float | None = None
            lsize: float | None = None
            if ml_fx.leslie_rate > 0:
                leslie = 1.0
                lrate = ml_fx.leslie_rate
                lsize = ml_fx.leslie_size
        else:
            # Fallback to Track.fx for backwards compatibility
            fx = track.fx
            room = cast(float, modulated.get("room", fx.room))
            size = cast(float, modulated.get("size", fx.size))
            dry = cast(float, modulated.get("dry", fx.dry))
            delay_send = cast(float, modulated.get("delay_send", fx.delay_send))
            delay_time = cast(float, modulated.get("delay_time", fx.delay_time))
            delay_feedback = cast(float, modulated.get("delay_feedback", fx.delay_feedback))
            leslie = None
            lrate = None
            lsize = None

        return SpatialFx(
            room=room,
            size=size,
            dry=dry,
            delay_send=delay_send,
            delay_time=delay_time,
            delay_feedback=delay_feedback,
            leslie=leslie,
            lrate=lrate,
            lsize=lsize,
        )

    def process_step_v2(self, state: RuntimeState) -> StepOutput:
        """
        Process all events at current step and return Output IR.

        This is the new implementation that returns a StepOutput (Layer 3)
        instead of sending OSC directly. The caller is responsible for
        sending the events.

        Args:
            state: Current runtime state (v5)

        Returns:
            StepOutput containing all events for this step
        """
        step = state.position.step
        cps = state.cps
        cycle = step / float(STEPS_PER_BAR)
        session = state.get_effective()

        osc_events: list[OscEvent] = []
        midi_notes: list[MidiNoteEvent] = []
        midi_ccs: list[MidiCCEvent] = []
        midi_pitch_bends: list[MidiPitchBendEvent] = []
        midi_aftertouches: list[MidiAftertouchEvent] = []

        # Process SuperDirt tracks
        for track_id, track in state.get_active_tracks().items():
            sequence = session.sequences.get(track_id)
            if not sequence:
                continue

            # Find the MixerLine this track belongs to
            mixer_line = self._find_mixer_line_for_track(track_id, session.mixer_lines)

            for event in sequence.get_events_at(step):
                # Main output (to the MixerLine the track belongs to)
                osc_event = self._build_osc_event(
                    track, event, step, cps, cycle,
                    mixer_line=mixer_line,
                    mixer_lines=session.mixer_lines,
                )
                osc_events.append(osc_event)

                # Send outputs (to other MixerLines via Track.sends)
                for send in track.sends:
                    target_ml = session.mixer_lines.get(send.target) if session.mixer_lines else None
                    if target_ml and target_ml != mixer_line:
                        send_event = self._build_osc_event(
                            track, event, step, cps, cycle,
                            mixer_line=target_ml,
                            mixer_lines=session.mixer_lines,
                            gain_multiplier=send.amount,
                        )
                        osc_events.append(send_event)

        # Process MIDI tracks
        for track_id, track_midi in state.get_active_tracks_midi().items():
            # Note events
            sequence = session.sequences.get(track_id)
            if sequence:
                for event in sequence.get_events_at(step):
                    midi_note = self._build_midi_note(track_midi, event, cps)
                    if midi_note is not None:
                        midi_notes.append(midi_note)

            # CC Modulations (sent every step)
            for cc_num, mod in track_midi.cc_modulations.items():
                signal_value = mod.signal[step]
                cc_event = self._build_midi_cc(track_midi.channel, cc_num, signal_value)
                midi_ccs.append(cc_event)

            # Pitch Bend Modulation
            if track_midi.pitch_bend_modulation:
                signal_value = track_midi.pitch_bend_modulation.signal[step]
                pb_event = self._build_midi_pitch_bend(track_midi.channel, signal_value)
                midi_pitch_bends.append(pb_event)

            # Aftertouch Modulation
            if track_midi.aftertouch_modulation:
                signal_value = track_midi.aftertouch_modulation.signal[step]
                at_event = self._build_midi_aftertouch(track_midi.channel, signal_value)
                midi_aftertouches.append(at_event)

        return StepOutput(
            step=step,
            osc_events=tuple(osc_events),
            midi_notes=tuple(midi_notes),
            midi_ccs=tuple(midi_ccs),
            midi_pitch_bends=tuple(midi_pitch_bends),
            midi_aftertouches=tuple(midi_aftertouches),
        )

    def _build_osc_event(
        self,
        track: Track,
        event: Event,
        step: int,
        cps: float,
        cycle: float,
        mixer_line: MixerLine | None = None,
        mixer_lines: dict[str, MixerLine] | None = None,
        gain_multiplier: float = 1.0,
    ) -> OscEvent:
        """
        Build OscEvent with all computations applied.

        Applies:
        - Velocity to gain (with optional multiplier for sends)
        - All modulations using PARAM_SPECS
        - Gate to sustain conversion
        - Spatial effects from MixerLine (v5) or Track.fx (fallback)

        Args:
            track: Track definition
            event: Event at this step
            step: Current step (for modulation lookup)
            cps: Cycles per second
            cycle: Current cycle position
            mixer_line: MixerLine the track belongs to (for spatial fx)
            mixer_lines: All MixerLines (for orbit calculation)
            gain_multiplier: Multiplier for gain (used for sends)

        Returns:
            OscEvent ready for transmission
        """
        params = track.params

        # Apply modulations to all parameters
        modulated = self._apply_all_modulations(track, step)

        # Base gain with velocity and multiplier applied
        final_gain = modulated.get("gain", params.gain) * event.velocity * gain_multiplier

        # Convert gate to sustain (seconds)
        sustain: float | None = None
        if event.gate is not None and cps > 0:
            sustain = event.gate / (cps * 16)

        # Get tone-shaping effects from TrackFxParams (tremolo/phaser)
        track_fx = track.track_fx

        # Get spatial effects (reverb, delay, leslie) from MixerLine or Track.fx
        spatial = self._get_spatial_fx(track, mixer_line, modulated)

        # Build params dict
        # Note: orbit and cps are NOT included here - extension will inject them via before_send_messages()
        # Store mixer_line_id if available for extension to use
        event_params = {}
        if mixer_line:
            event_params["mixer_line_id"] = mixer_line.name

        # Build extra_params tuple for SynthDef-specific params
        extra_params_tuple = tuple(params.extra_params.items()) if params.extra_params else ()

        return OscEvent(
            sound=params.s,
            params=event_params,
            cycle=cycle,
            # Sound params (with modulation)
            gain=final_gain,
            pan=modulated.get("pan", params.pan),
            n=params.n,
            speed=modulated.get("speed", params.speed),
            begin=params.begin,
            end=params.end,
            midinote=event.note,
            sustain=sustain,
            cut=params.cut,
            legato=params.legato,
            # Filter (from track_fx)
            cutoff=modulated.get("cutoff", track_fx.cutoff),
            resonance=modulated.get("resonance", track_fx.resonance),
            hcutoff=modulated.get("hcutoff", track_fx.hcutoff),
            hresonance=modulated.get("hresonance", track_fx.hresonance),
            bandf=track_fx.bandf,
            bandq=track_fx.bandq,
            vowel=track_fx.vowel,
            # Reverb (from MixerLine.fx or Track.fx fallback)
            room=spatial.room,
            size=spatial.size,
            dry=spatial.dry,
            # Delay (from MixerLine.fx or Track.fx fallback)
            delay_send=spatial.delay_send,
            delaytime=spatial.delay_time,
            delayfeedback=spatial.delay_feedback,
            # Distortion (from track_fx)
            shape=modulated.get("shape", track_fx.shape),
            crush=modulated.get("crush", track_fx.crush),
            coarse=track_fx.coarse,
            krush=track_fx.krush,
            kcutoff=track_fx.kcutoff,
            triode=track_fx.triode,
            # Envelope (from track_fx)
            attack=modulated.get("attack", track_fx.attack),
            hold=modulated.get("hold", track_fx.hold),
            release=modulated.get("release", track_fx.release),
            # Tremolo/Phaser from TrackFxParams
            tremolorate=track_fx.tremolo_rate,
            tremolodepth=track_fx.tremolo_depth,
            phaserrate=track_fx.phaser_rate,
            phaserdepth=track_fx.phaser_depth,
            # Leslie (from MixerLine.fx)
            leslie=spatial.leslie,
            lrate=spatial.lrate,
            lsize=spatial.lsize,
            # Pitch
            detune=track_fx.detune,
            accelerate=track_fx.accelerate,
            psrate=track_fx.psrate,
            psdisp=track_fx.psdisp,
            # Spectral/FFT
            freeze=track_fx.freeze,
            smear=track_fx.smear,
            binshift=track_fx.binshift,
            comb=track_fx.comb,
            scram=track_fx.scram,
            hbrick=track_fx.hbrick,
            lbrick=track_fx.lbrick,
            enhance=track_fx.enhance,
            tsdelay=track_fx.tsdelay,
            xsdelay=track_fx.xsdelay,
            # Ring modulation
            ring=track_fx.ring,
            ringf=track_fx.ringf,
            ringdf=track_fx.ringdf,
            # Additional effects
            squiz=track_fx.squiz,
            waveloss=track_fx.waveloss,
            octer=track_fx.octer,
            octersub=track_fx.octersub,
            octersubsub=track_fx.octersubsub,
            fshift=track_fx.fshift,
            fshiftnote=track_fx.fshiftnote,
            fshiftphase=track_fx.fshiftphase,
            djf=track_fx.djf,
            # Compressor
            cthresh=track_fx.cthresh,
            cratio=track_fx.cratio,
            cattack=track_fx.cattack,
            crelease=track_fx.crelease,
            cgain=track_fx.cgain,
            cknee=track_fx.cknee,
            # Pan extras
            panspread=track_fx.panspread,
            # SynthDef-specific extra params
            extra_params=extra_params_tuple,
        )

    def _apply_all_modulations(
        self,
        track: Track,
        step: int,
    ) -> dict[str, float]:
        """
        Apply all modulations to track parameters at given step.

        Uses PARAM_SPECS to determine modulation type (additive, multiplicative, bipolar)
        and apply_modulation() for correct value calculation.

        Args:
            track: Track definition with modulations
            step: Current step (0-255)

        Returns:
            Dictionary of param_name -> modulated_value
        """
        result: dict[str, float] = {}
        params = track.params
        fx = track.fx

        # Base values for each parameter
        base_values: dict[str, float] = {
            # Sound params
            "gain": params.gain,
            "pan": params.pan,
            "speed": params.speed,
            # Filter
            "cutoff": fx.cutoff if fx.cutoff is not None else 1000.0,
            "resonance": fx.resonance if fx.resonance is not None else 0.0,
            "hcutoff": fx.hcutoff if fx.hcutoff is not None else 5000.0,
            "hresonance": fx.hresonance if fx.hresonance is not None else 0.0,
            # Reverb
            "room": fx.room if fx.room is not None else 0.0,
            "size": fx.size if fx.size is not None else 0.5,
            "dry": fx.dry if fx.dry is not None else 1.0,
            # Delay
            "delay_send": fx.delay_send if fx.delay_send is not None else 0.0,
            "delay_time": fx.delay_time if fx.delay_time is not None else 0.0,
            "delay_feedback": fx.delay_feedback if fx.delay_feedback is not None else 0.0,
            # Distortion
            "shape": fx.shape if fx.shape is not None else 0.0,
            "crush": fx.crush if fx.crush is not None else 16.0,
            # Envelope
            "attack": fx.attack if fx.attack is not None else 0.001,
            "hold": fx.hold if fx.hold is not None else 0.0,
            "release": fx.release if fx.release is not None else 0.2,
        }

        # Apply modulations
        for param_name, modulation in track.modulations.items():
            # Resolve hierarchical path (e.g., "filter.cutoff" -> "cutoff")
            resolved_name = self._resolve_param_name(param_name)

            if resolved_name not in PARAM_SPECS:
                continue

            spec = PARAM_SPECS[resolved_name]
            base_value = base_values.get(resolved_name, spec.default)
            signal_value = modulation.signal[step]

            result[resolved_name] = apply_modulation(base_value, signal_value, spec)

        return result

    def _resolve_param_name(self, name: str) -> str:
        """
        Resolve hierarchical parameter name to OSC parameter name.

        Examples:
            "filter.cutoff" -> "cutoff"
            "reverb.room" -> "room"
            "cutoff" -> "cutoff"

        Args:
            name: Parameter name (flat or hierarchical)

        Returns:
            Resolved flat parameter name
        """
        # Hierarchical path mapping
        path_map = {
            "filter.cutoff": "cutoff",
            "filter.resonance": "resonance",
            "filter.hcutoff": "hcutoff",
            "filter.hresonance": "hresonance",
            "reverb.room": "room",
            "reverb.size": "size",
            "reverb.dry": "dry",
            "delay.send": "delay_send",
            "delay.time": "delay_time",
            "delay.feedback": "delay_feedback",
            "distortion.shape": "shape",
            "distortion.crush": "crush",
            "envelope.attack": "attack",
            "envelope.hold": "hold",
            "envelope.release": "release",
        }

        return path_map.get(name, name)

    def _build_midi_note(
        self,
        track_midi: TrackMidi,
        event: Event,
        cps: float,
    ) -> MidiNoteEvent | None:
        """
        Build MidiNoteEvent from track and event.

        Applies:
        - Transpose to note
        - Velocity scaling
        - Gate to duration conversion

        Args:
            track_midi: MIDI track definition
            event: Event at this step
            cps: Cycles per second (for duration calculation)

        Returns:
            MidiNoteEvent or None if no note
        """
        if event.note is None:
            return None

        # Apply transpose and clamp to MIDI range
        note = event.note + track_midi.transpose
        note = max(0, min(127, note))

        # Calculate velocity (event velocity * track default)
        velocity = int(event.velocity * track_midi.velocity)
        velocity = max(0, min(127, velocity))

        # Calculate duration in milliseconds
        if cps > 0 and event.gate is not None:
            duration_ms = int((event.gate / (cps * 16)) * 1000)
        else:
            duration_ms = 250  # Default 250ms

        return MidiNoteEvent(
            channel=track_midi.channel,
            note=note,
            velocity=velocity,
            duration_ms=duration_ms,
        )

    def _build_midi_cc(
        self,
        channel: int,
        cc_num: int,
        signal_value: float,
    ) -> MidiCCEvent:
        """
        Build MidiCCEvent from modulation signal.

        Converts signal value (-1.0 to +1.0) to MIDI CC value (0-127).

        Args:
            channel: MIDI channel
            cc_num: CC number
            signal_value: Signal value from StepBuffer (-1.0 to +1.0)

        Returns:
            MidiCCEvent ready for transmission
        """
        # Convert -1.0~+1.0 to 0~127
        value = int((signal_value + 1.0) / 2.0 * 127)
        value = max(0, min(127, value))

        return MidiCCEvent(
            channel=channel,
            cc=cc_num,
            value=value,
        )

    def _build_midi_pitch_bend(
        self,
        channel: int,
        signal_value: float,
    ) -> MidiPitchBendEvent:
        """
        Build MidiPitchBendEvent from modulation signal.

        Converts signal value (-1.0 to +1.0) to pitch bend (-8192 to 8191).

        Args:
            channel: MIDI channel
            signal_value: Signal value from StepBuffer (-1.0 to +1.0)

        Returns:
            MidiPitchBendEvent ready for transmission
        """
        # Convert -1.0~+1.0 to -8192~8191
        value = int(signal_value * 8191)
        value = max(-8192, min(8191, value))

        return MidiPitchBendEvent(
            channel=channel,
            value=value,
        )

    def _build_midi_aftertouch(
        self,
        channel: int,
        signal_value: float,
    ) -> MidiAftertouchEvent:
        """
        Build MidiAftertouchEvent from modulation signal.

        Converts signal value (-1.0 to +1.0) to aftertouch (0-127).
        Note: Signal is mapped to 0-127, negative values clamp to 0.

        Args:
            channel: MIDI channel
            signal_value: Signal value from StepBuffer (-1.0 to +1.0)

        Returns:
            MidiAftertouchEvent ready for transmission
        """
        # Convert -1.0~+1.0 to 0~127 (same as CC)
        value = int((signal_value + 1.0) / 2.0 * 127)
        value = max(0, min(127, value))

        return MidiAftertouchEvent(
            channel=channel,
            value=value,
        )
