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
    "BPM",
    "Milliseconds",
    "validate_offset",
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


# Validation utilities
def validate_offset(offset: float) -> float:
    """Validate offset is in [0.0, 1.0) range.

    Args:
        offset: Offset value to validate

    Returns:
        The validated offset value

    Raises:
        ValueError: If offset is not in [0.0, 1.0) range

    Example:
        >>> validate_offset(0.0)
        0.0
        >>> validate_offset(0.5)
        0.5
        >>> validate_offset(0.999)
        0.999
        >>> validate_offset(1.0)  # doctest: +SKIP
        ValueError: Offset must be in range [0.0, 1.0), got 1.0
    """
    if not (0.0 <= offset < 1.0):
        raise ValueError(f"Offset must be in range [0.0, 1.0), got {offset}")
    return offset


# Conversion utilities
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
