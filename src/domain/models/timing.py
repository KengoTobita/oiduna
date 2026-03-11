"""
Timing type definitions for Oiduna.

Provides NewType wrappers for timing-related units to prevent mixing
different units at the type level. These types have no runtime cost
and are purely for static type checking with mypy.

Usage:
    >>> from oiduna_models.timing import StepNumber, BeatNumber
    >>> step: StepNumber = StepNumber(0)
    >>> beat: BeatNumber = BeatNumber(4)
    >>> # mypy error: Argument 1 has incompatible type "BeatNumber"; expected "StepNumber"
    >>> get_messages_for_step(beat)  # Type error!
"""

from typing import NewType

__all__ = [
    "StepNumber",
    "BeatNumber",
    "BarNumber",
    "CycleFloat",
    "BPM",
    "Milliseconds",
]

# Timing units (quantized positions in the 256-step loop)
StepNumber = NewType("StepNumber", int)
"""Step number in the 256-step loop (0-255).

1 step = 1/16 note
256 steps = 1 loop
"""

BeatNumber = NewType("BeatNumber", int)
"""Beat number in the 16-beat loop (0-15).

1 beat = 4 steps = 1/4 note
16 beats = 1 loop
"""

BarNumber = NewType("BarNumber", int)
"""Bar (measure) number in the 4-bar loop (0-3).

1 bar = 16 steps = 4 beats
4 bars = 1 loop
"""

# Timing units (precise floating-point positions)
CycleFloat = NewType("CycleFloat", float)
"""Precise cycle position (0.0-4.0).

1.0 cycle = 64 steps = 4 beats = 1 bar
4.0 cycles = 256 steps = 1 loop

Used for precise timing in TidalCycles-compatible events.
"""

# Tempo
BPM = NewType("BPM", int)
"""Beats per minute (20-999).

Determines the playback speed of the loop.
At 120 BPM: 1 step = 125ms, 1 beat = 500ms, 1 loop = 32s
"""

# Duration
Milliseconds = NewType("Milliseconds", int)
"""Duration in milliseconds.

Used for timing intervals, durations, and thresholds.
"""


# Conversion utilities
def step_to_cycle(step: StepNumber) -> CycleFloat:
    """Convert step number to cycle position.

    Args:
        step: Step number (0-255)

    Returns:
        Cycle position (0.0-3.996...)

    Example:
        >>> step_to_cycle(StepNumber(0))
        0.0
        >>> step_to_cycle(StepNumber(64))
        1.0
        >>> step_to_cycle(StepNumber(256))  # Out of range but demonstrates formula
        4.0
    """
    return CycleFloat((step / 256.0) * 4.0)


def cycle_to_step(cycle: CycleFloat) -> StepNumber:
    """Convert cycle position to quantized step number.

    Args:
        cycle: Cycle position (0.0-4.0)

    Returns:
        Quantized step number (0-255)

    Example:
        >>> cycle_to_step(CycleFloat(0.0))
        0
        >>> cycle_to_step(CycleFloat(1.0))
        64
        >>> cycle_to_step(CycleFloat(3.996))
        255
    """
    return StepNumber(int((cycle / 4.0) * 256))


def step_to_beat(step: StepNumber) -> BeatNumber:
    """Convert step number to beat number.

    Args:
        step: Step number (0-255)

    Returns:
        Beat number (0-15)

    Example:
        >>> step_to_beat(StepNumber(0))
        0
        >>> step_to_beat(StepNumber(4))
        1
        >>> step_to_beat(StepNumber(64))
        0  # Wraps around (64 % 16 = 0)
    """
    return BeatNumber((step // 4) % 16)


def step_to_bar(step: StepNumber) -> BarNumber:
    """Convert step number to bar number.

    Args:
        step: Step number (0-255)

    Returns:
        Bar number (0-3)

    Example:
        >>> step_to_bar(StepNumber(0))
        0
        >>> step_to_bar(StepNumber(16))
        1
        >>> step_to_bar(StepNumber(64))
        0  # Wraps around (64 // 16) % 4 = 0
    """
    return BarNumber((step // 16) % 4)


def bpm_to_step_duration_ms(bpm: BPM) -> Milliseconds:
    """Calculate step duration in milliseconds for given BPM.

    Args:
        bpm: Beats per minute

    Returns:
        Duration of one step in milliseconds

    Example:
        >>> bpm_to_step_duration_ms(BPM(120))
        125
        >>> bpm_to_step_duration_ms(BPM(60))
        250
        >>> bpm_to_step_duration_ms(BPM(180))
        83
    """
    # 1 beat = 60000 / bpm milliseconds
    # 1 step = 1/4 beat
    beat_duration_ms = 60000.0 / bpm
    step_duration_ms = beat_duration_ms / 4.0
    return Milliseconds(int(step_duration_ms))


def bpm_to_loop_duration_ms(bpm: BPM) -> Milliseconds:
    """Calculate loop duration in milliseconds for given BPM.

    Args:
        bpm: Beats per minute

    Returns:
        Duration of one loop (256 steps) in milliseconds

    Example:
        >>> bpm_to_loop_duration_ms(BPM(120))
        32000  # 32 seconds
        >>> bpm_to_loop_duration_ms(BPM(60))
        64000  # 64 seconds
    """
    # 1 loop = 256 steps = 64 beats (4 steps per beat)
    beat_duration_ms = 60000.0 / bpm
    loop_duration_ms = beat_duration_ms * 64
    return Milliseconds(int(loop_duration_ms))
