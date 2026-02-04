"""
Output IR: Layer 3 of the Three-Layer IR Architecture.

This module defines the final output format for OSC/MIDI messages.
All values are pre-computed (velocity applied, gate converted to seconds,
modulation applied) and ready for direct transmission.

Design principles:
- frozen=True, slots=True for zero GC impact
- All values are final (no further computation needed by sender)
- Immutable for thread safety and predictability

See: docs/plans/THREE_LAYER_IR_ARCHITECTURE.md
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# ===========================================================================
# OSC Output (SuperDirt)
# ===========================================================================


@dataclass(frozen=True, slots=True)
class OscEvent:
    """
    SuperDirt OSC event - ready for transmission.

    All values are pre-computed:
    - gain includes velocity and modulation
    - sustain is in seconds (not gate steps)
    - all modulations are applied

    Example:
        >>> event = OscEvent(
        ...     sound="super808",
        ...     orbit=0,
        ...     cps=0.5,
        ...     cycle=3.0,
        ...     gain=0.72,  # 0.8 * 0.9 (velocity)
        ...     pan=0.5,
        ... )
        >>> event.to_osc_args()
        ['s', 'super808', 'orbit', 0, 'cps', 0.5, ...]
    """

    # === Required: Core Sound ===
    sound: str  # "s" - sound name (e.g., "super808", "bd", "piano")
    orbit: int  # track routing (0-11)

    # === Required: Timing ===
    cps: float  # cycles per second (derived from BPM)
    cycle: float  # current cycle position

    # === Required: Basic Params ===
    gain: float  # final gain (base × velocity × modulation)
    pan: float  # 0.0 (left) to 1.0 (right)

    # === Optional: Sample Control ===
    n: int = 0  # sample number within sound bank
    speed: float = 1.0  # playback speed (negative = reverse)
    begin: float = 0.0  # sample start point (0.0-1.0)
    end: float = 1.0  # sample end point (0.0-1.0)

    # === Optional: Note ===
    midinote: int | None = None  # MIDI note number (for synths)
    sustain: float | None = None  # note duration in seconds

    # === Optional: Voice Control ===
    cut: int | None = None  # cut group (notes in same group cut each other)
    legato: float | None = None  # legato mode (note length multiplier)

    # === Optional: Filter ===
    cutoff: float | None = None  # low-pass filter cutoff (Hz)
    resonance: float | None = None  # filter resonance (0.0-1.0)
    hcutoff: float | None = None  # high-pass filter cutoff (Hz)
    hresonance: float | None = None  # high-pass resonance
    bandf: float | None = None  # band-pass center frequency
    bandq: float | None = None  # band-pass Q

    # === Optional: Reverb ===
    room: float | None = None  # reverb room size (0.0-1.0)
    size: float | None = None  # reverb size
    dry: float | None = None  # dry signal level

    # === Optional: Delay ===
    delay_send: float | None = None  # delay send level (SuperDirt: delaySend)
    delaytime: float | None = None  # delay time
    delayfeedback: float | None = None  # delay feedback

    # === Optional: Distortion ===
    shape: float | None = None  # waveshaping amount
    crush: float | None = None  # bit crush
    coarse: float | None = None  # sample rate reduction

    # === Optional: Envelope ===
    attack: float | None = None  # attack time
    hold: float | None = None  # hold time
    release: float | None = None  # release time

    # === Optional: Modulation (Tremolo/Phaser) ===
    tremolorate: float | None = None  # tremolo LFO rate (Hz)
    tremolodepth: float | None = None  # tremolo depth (0-1)
    phaserrate: float | None = None  # phaser LFO rate (Hz)
    phaserdepth: float | None = None  # phaser depth (0-1)

    # === Optional: Leslie (Global Effect) ===
    leslie: float | None = None  # leslie effect on/off
    lrate: float | None = None  # leslie LFO rate (Hz)
    lsize: float | None = None  # leslie size/speed

    # === Optional: Pitch ===
    detune: float | None = None  # detune amount
    accelerate: float | None = None  # pitch acceleration over time
    psrate: float | None = None  # pitch shift rate (ratio)
    psdisp: float | None = None  # pitch shift time dispersion

    # === Optional: Vowel/Formant ===
    vowel: str | None = None  # vowel shape (a, e, i, o, u)

    # === Optional: Spectral/FFT Effects ===
    freeze: float | None = None  # FFT freeze (0-1)
    smear: float | None = None  # spectral smearing
    binshift: float | None = None  # FFT bin shifting
    comb: float | None = None  # spectral comb filter
    scram: float | None = None  # spectral scramble
    hbrick: float | None = None  # spectral high-pass brick wall
    lbrick: float | None = None  # spectral low-pass brick wall
    enhance: float | None = None  # spectral enhancement
    tsdelay: float | None = None  # spectral delay time
    xsdelay: float | None = None  # spectral delay mix pattern

    # === Optional: Ring Modulation ===
    ring: float | None = None  # ring modulation amount
    ringf: float | None = None  # ring modulation frequency (Hz)
    ringdf: float | None = None  # ring frequency slide (Hz)

    # === Optional: Additional Effects ===
    squiz: float | None = None  # squiz pitch ratio
    waveloss: float | None = None  # wave segment drop percentage
    octer: float | None = None  # octave-up harmonics
    octersub: float | None = None  # half-frequency harmonics
    octersubsub: float | None = None  # quarter-frequency harmonics
    fshift: float | None = None  # frequency shift (Hz)
    fshiftnote: float | None = None  # shift as fraction of note freq
    fshiftphase: float | None = None  # shift phase (radians)
    krush: float | None = None  # Sonic Pi krush distortion
    kcutoff: float | None = None  # krush filter cutoff (Hz)
    triode: float | None = None  # triode tube distortion drive
    djf: float | None = None  # DJ filter position (0=LP, 0.5=bypass, 1=HP)

    # === Optional: Compressor ===
    cthresh: float | None = None  # compression threshold
    cratio: float | None = None  # compression ratio
    cattack: float | None = None  # compressor attack time
    crelease: float | None = None  # compressor release time
    cgain: float | None = None  # compressor output gain
    cknee: float | None = None  # soft knee amount

    # === Optional: Pan/Delay Extras ===
    panspread: float | None = None  # stereo spread
    delayamp: float | None = None  # delay output amplitude
    lock: int | None = None  # tempo sync delay (0/1)

    # === Optional: Synth Extra Params (dynamic) ===
    extra_params: tuple[tuple[str, Any], ...] = ()  # SynthDef-specific params

    def to_osc_args(self) -> list[Any]:
        """
        Convert to SuperDirt OSC message format.

        Returns:
            List in [key, value, key, value, ...] format
            ready for pythonosc send_message()
        """
        # Required params (always included)
        args: list[Any] = [
            "s",
            self.sound,
            "orbit",
            self.orbit,
            "cps",
            self.cps,
            "cycle",
            self.cycle,
            "gain",
            self.gain,
            "pan",
            self.pan,
            "n",
            self.n,
            "speed",
            self.speed,
            "begin",
            self.begin,
            "end",
            self.end,
        ]

        # Optional params (only include if set)
        optionals: list[tuple[str, Any]] = [
            ("midinote", self.midinote),
            ("sustain", self.sustain),
            ("cut", self.cut),
            ("legato", self.legato),
            # Filter
            ("cutoff", self.cutoff),
            ("resonance", self.resonance),
            ("hcutoff", self.hcutoff),
            ("hresonance", self.hresonance),
            ("bandf", self.bandf),
            ("bandq", self.bandq),
            # Reverb
            ("room", self.room),
            ("size", self.size),
            ("dry", self.dry),
            # Delay
            ("delaySend", self.delay_send),  # SuperDirt expects "delaySend"
            ("delaytime", self.delaytime),
            ("delayfeedback", self.delayfeedback),
            ("delayAmp", self.delayamp),  # SuperDirt expects "delayAmp"
            ("lock", self.lock),
            # Distortion
            ("shape", self.shape),
            ("crush", self.crush),
            ("coarse", self.coarse),
            # Envelope
            ("attack", self.attack),
            ("hold", self.hold),
            ("release", self.release),
            # Modulation
            ("tremolorate", self.tremolorate),
            ("tremolodepth", self.tremolodepth),
            ("phaserrate", self.phaserrate),
            ("phaserdepth", self.phaserdepth),
            # Leslie
            ("leslie", self.leslie),
            ("lrate", self.lrate),
            ("lsize", self.lsize),
            # Pitch
            ("detune", self.detune),
            ("accelerate", self.accelerate),
            ("psrate", self.psrate),
            ("psdisp", self.psdisp),
            # Vowel
            ("vowel", self.vowel),
            # Spectral/FFT
            ("freeze", self.freeze),
            ("smear", self.smear),
            ("binshift", self.binshift),
            ("comb", self.comb),
            ("scram", self.scram),
            ("hbrick", self.hbrick),
            ("lbrick", self.lbrick),
            ("enhance", self.enhance),
            ("tsdelay", self.tsdelay),
            ("xsdelay", self.xsdelay),
            # Ring modulation
            ("ring", self.ring),
            ("ringf", self.ringf),
            ("ringdf", self.ringdf),
            # Additional effects
            ("squiz", self.squiz),
            ("waveloss", self.waveloss),
            ("octer", self.octer),
            ("octersub", self.octersub),
            ("octersubsub", self.octersubsub),
            ("fshift", self.fshift),
            ("fshiftnote", self.fshiftnote),
            ("fshiftphase", self.fshiftphase),
            ("krush", self.krush),
            ("kcutoff", self.kcutoff),
            ("triode", self.triode),
            ("djf", self.djf),
            # Compressor
            ("cThresh", self.cthresh),  # SuperDirt expects camelCase
            ("cRatio", self.cratio),
            ("cAttack", self.cattack),
            ("cRelease", self.crelease),
            ("cGain", self.cgain),
            ("cKnee", self.cknee),
            # Pan extras
            ("panspread", self.panspread),
        ]

        for key, value in optionals:
            if value is not None:
                args.extend([key, value])

        # Add synth-specific extra params
        for key, value in self.extra_params:
            args.extend([key, value])

        return args

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary (for debugging/logging)."""
        result: dict[str, Any] = {
            "sound": self.sound,
            "orbit": self.orbit,
            "cps": self.cps,
            "cycle": self.cycle,
            "gain": self.gain,
            "pan": self.pan,
            "n": self.n,
            "speed": self.speed,
            "begin": self.begin,
            "end": self.end,
        }

        # Add optional fields if set
        for field in [
            "midinote",
            "sustain",
            "cut",
            "legato",
            # Filter
            "cutoff",
            "resonance",
            "hcutoff",
            "hresonance",
            "bandf",
            "bandq",
            # Reverb
            "room",
            "size",
            "dry",
            # Delay
            "delay_send",
            "delaytime",
            "delayfeedback",
            "delayamp",
            "lock",
            # Distortion
            "shape",
            "crush",
            "coarse",
            # Envelope
            "attack",
            "hold",
            "release",
            # Modulation
            "tremolorate",
            "tremolodepth",
            "phaserrate",
            "phaserdepth",
            # Leslie
            "leslie",
            "lrate",
            "lsize",
            # Pitch
            "detune",
            "accelerate",
            "psrate",
            "psdisp",
            # Vowel
            "vowel",
            # Spectral/FFT
            "freeze",
            "smear",
            "binshift",
            "comb",
            "scram",
            "hbrick",
            "lbrick",
            "enhance",
            "tsdelay",
            "xsdelay",
            # Ring modulation
            "ring",
            "ringf",
            "ringdf",
            # Additional effects
            "squiz",
            "waveloss",
            "octer",
            "octersub",
            "octersubsub",
            "fshift",
            "fshiftnote",
            "fshiftphase",
            "krush",
            "kcutoff",
            "triode",
            "djf",
            # Compressor
            "cthresh",
            "cratio",
            "cattack",
            "crelease",
            "cgain",
            "cknee",
            # Pan extras
            "panspread",
        ]:
            value = getattr(self, field)
            if value is not None:
                result[field] = value

        # Add extra params
        if self.extra_params:
            result["extra_params"] = dict(self.extra_params)

        return result


# ===========================================================================
# MIDI Output
# ===========================================================================


@dataclass(frozen=True, slots=True)
class MidiNoteEvent:
    """
    MIDI Note event - ready for transmission.

    Values are final:
    - note is transposed
    - velocity is scaled and clamped to 0-127
    - duration is in milliseconds

    Example:
        >>> note = MidiNoteEvent(
        ...     channel=0,
        ...     note=60,  # C4, already transposed
        ...     velocity=100,
        ...     duration_ms=250,
        ... )
    """

    channel: int  # MIDI channel 0-15
    note: int  # MIDI note 0-127 (transposed)
    velocity: int  # MIDI velocity 0-127 (final)
    duration_ms: int  # note duration in milliseconds

    def __post_init__(self) -> None:
        """Validate MIDI ranges (development safety check)."""
        if not 0 <= self.channel <= 15:
            raise ValueError(f"Invalid MIDI channel: {self.channel} (must be 0-15)")
        if not 0 <= self.note <= 127:
            raise ValueError(f"Invalid MIDI note: {self.note} (must be 0-127)")
        if not 0 <= self.velocity <= 127:
            raise ValueError(f"Invalid MIDI velocity: {self.velocity} (must be 0-127)")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary (for debugging/logging)."""
        return {
            "channel": self.channel,
            "note": self.note,
            "velocity": self.velocity,
            "duration_ms": self.duration_ms,
        }


@dataclass(frozen=True, slots=True)
class MidiCCEvent:
    """
    MIDI Control Change event - ready for transmission.

    Used for modulation output (e.g., filter cutoff automation).

    Example:
        >>> cc = MidiCCEvent(channel=0, cc=74, value=64)  # Cutoff at center
    """

    channel: int  # MIDI channel 0-15
    cc: int  # CC number 0-127
    value: int  # CC value 0-127

    def __post_init__(self) -> None:
        """Validate MIDI ranges."""
        if not 0 <= self.channel <= 15:
            raise ValueError(f"Invalid MIDI channel: {self.channel}")
        if not 0 <= self.cc <= 127:
            raise ValueError(f"Invalid CC number: {self.cc}")
        if not 0 <= self.value <= 127:
            raise ValueError(f"Invalid CC value: {self.value}")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "channel": self.channel,
            "cc": self.cc,
            "value": self.value,
        }


@dataclass(frozen=True, slots=True)
class MidiPitchBendEvent:
    """
    MIDI Pitch Bend event - ready for transmission.

    Value is in MIDI 14-bit signed format (-8192 to 8191).
    Center (no bend) is 0.

    Example:
        >>> pb = MidiPitchBendEvent(channel=0, value=4096)  # Bend up
    """

    channel: int  # MIDI channel 0-15
    value: int  # Pitch bend value -8192 to 8191 (0 = center)

    def __post_init__(self) -> None:
        """Validate MIDI ranges."""
        if not 0 <= self.channel <= 15:
            raise ValueError(f"Invalid MIDI channel: {self.channel}")
        if not -8192 <= self.value <= 8191:
            raise ValueError(f"Invalid pitch bend value: {self.value}")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "channel": self.channel,
            "value": self.value,
        }


@dataclass(frozen=True, slots=True)
class MidiAftertouchEvent:
    """
    MIDI Channel Aftertouch (Pressure) event - ready for transmission.

    Value is 0-127, converted from signal (0.0 to 1.0).

    Example:
        >>> at = MidiAftertouchEvent(channel=0, value=64)  # Medium pressure
    """

    channel: int  # MIDI channel 0-15
    value: int  # Aftertouch value 0-127

    def __post_init__(self) -> None:
        """Validate MIDI ranges."""
        if not 0 <= self.channel <= 15:
            raise ValueError(f"Invalid MIDI channel: {self.channel}")
        if not 0 <= self.value <= 127:
            raise ValueError(f"Invalid aftertouch value: {self.value}")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "channel": self.channel,
            "value": self.value,
        }


# ===========================================================================
# Step Output (Aggregate)
# ===========================================================================


@dataclass(frozen=True, slots=True)
class StepOutput:
    """
    Complete output for a single step.

    Aggregates all OSC and MIDI events to be sent at this step.
    This is the final output of StepProcessor - the complete
    Layer 3 Output IR for one timing tick.

    Design:
    - Uses tuple (not list) for immutability
    - All events are pre-computed and ready for transmission
    - Can be inspected for testing/debugging

    Example:
        >>> output = processor.process_step(state)
        >>> for event in output.osc_events:
        ...     sender.send(event.to_osc_args())
        >>> for note in output.midi_notes:
        ...     midi.send_note(note)
    """

    step: int  # Current step (0-255)
    osc_events: tuple[OscEvent, ...]  # SuperDirt events
    midi_notes: tuple[MidiNoteEvent, ...]  # MIDI note events
    midi_ccs: tuple[MidiCCEvent, ...]  # MIDI CC events
    midi_pitch_bends: tuple[MidiPitchBendEvent, ...] = ()  # Pitch bend events
    midi_aftertouches: tuple[MidiAftertouchEvent, ...] = ()  # Aftertouch events

    @property
    def is_empty(self) -> bool:
        """Check if this step has no events."""
        return (
            len(self.osc_events) == 0
            and len(self.midi_notes) == 0
            and len(self.midi_ccs) == 0
            and len(self.midi_pitch_bends) == 0
            and len(self.midi_aftertouches) == 0
        )

    @property
    def event_count(self) -> int:
        """Total number of events."""
        return (
            len(self.osc_events)
            + len(self.midi_notes)
            + len(self.midi_ccs)
            + len(self.midi_pitch_bends)
            + len(self.midi_aftertouches)
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary (for debugging/logging)."""
        return {
            "step": self.step,
            "osc_events": [e.to_dict() for e in self.osc_events],
            "midi_notes": [n.to_dict() for n in self.midi_notes],
            "midi_ccs": [c.to_dict() for c in self.midi_ccs],
            "midi_pitch_bends": [p.to_dict() for p in self.midi_pitch_bends],
            "midi_aftertouches": [a.to_dict() for a in self.midi_aftertouches],
        }


# ===========================================================================
# Factory Functions
# ===========================================================================


def create_empty_step_output(step: int) -> StepOutput:
    """Create an empty StepOutput for a given step."""
    return StepOutput(
        step=step,
        osc_events=(),
        midi_notes=(),
        midi_ccs=(),
    )
