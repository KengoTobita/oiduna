"""SignalExpr - Signal expression data types for Oiduna Framework.

Represents signal sources and effect chains as an intermediate representation.
DSL parses to SignalExpr, then SignalBuilder converts to StepBuffer.

Example DSL flow:
    sin(4, 0.5) | noise(0.1) | clip(-0.8, 0.8)
        ↓
    SignalExpr(
        source=LfoSource("sin", cycles=4, amount=0.5),
        effects=(AddNoiseEffect(0.1), ClipEffect(-0.8, 0.8))
    )
        ↓
    SignalBuilder.build(expr) → StepBuffer
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Union

# =============================================================================
# Signal Sources - What generates the base signal
# =============================================================================

WaveformType = Literal["sin", "tri", "saw", "square"]


@dataclass(frozen=True, slots=True)
class WaveformSource:
    """Basic waveform generator.

    Args:
        waveform: Wave shape type
        rate: Steps per cycle (e.g., 16 = one cycle per bar)
        amount: Amplitude scaling (-1.0 to +1.0)
        phase: Phase offset (0.0 to 1.0)
    """

    waveform: WaveformType
    rate: float
    amount: float = 1.0
    phase: float = 0.0


@dataclass(frozen=True, slots=True)
class LfoSource:
    """LFO generator with cycles per loop.

    Args:
        waveform: Wave shape type
        cycles: Number of cycles per 256-step loop
        amount: Amplitude scaling
        phase: Phase offset
    """

    waveform: WaveformType
    cycles: float
    amount: float = 1.0
    phase: float = 0.0


@dataclass(frozen=True, slots=True)
class RandomSource:
    """Deterministic random signal.

    Args:
        seed: Random seed (None for time-based)
        amount: Amplitude scaling
    """

    seed: int | None = None
    amount: float = 1.0


@dataclass(frozen=True, slots=True)
class EnvelopeSource:
    """AHR envelope generator.

    Args:
        attack: Attack time in steps
        hold: Hold time in steps
        release: Release time in steps
        amount: Peak amplitude
    """

    attack: int = 16
    hold: int = 32
    release: int = 48
    amount: float = 1.0


@dataclass(frozen=True, slots=True)
class StepSequenceSource:
    """Step sequence from discrete values.

    Args:
        values: Tuple of values to sequence
        steps_per_value: Steps to hold each value
    """

    values: tuple[float, ...]
    steps_per_value: int = 16


@dataclass(frozen=True, slots=True)
class ConstantSource:
    """Constant value signal.

    Args:
        value: The constant value
    """

    value: float


# Union of all signal source types
SignalSource = Union[
    WaveformSource,
    LfoSource,
    RandomSource,
    EnvelopeSource,
    StepSequenceSource,
    ConstantSource,
]


# =============================================================================
# Signal Effects - Transformations applied to signals
# =============================================================================


@dataclass(frozen=True, slots=True)
class ClipEffect:
    """Clip (hard limit) signal to range.

    Args:
        min_val: Minimum value
        max_val: Maximum value
    """

    min_val: float = -1.0
    max_val: float = 1.0


@dataclass(frozen=True, slots=True)
class ScaleEffect:
    """Scale signal by factor.

    Args:
        factor: Multiplication factor
    """

    factor: float


@dataclass(frozen=True, slots=True)
class OffsetEffect:
    """Add constant offset to signal.

    Args:
        value: Offset to add
    """

    value: float


@dataclass(frozen=True, slots=True)
class AddNoiseEffect:
    """Add random noise to signal.

    Args:
        amount: Noise amplitude (0.0 to 1.0)
        seed: Random seed for reproducibility
    """

    amount: float = 0.1
    seed: int | None = None


@dataclass(frozen=True, slots=True)
class QuantizeEffect:
    """Quantize signal to discrete levels.

    Args:
        levels: Number of quantization levels
    """

    levels: int


@dataclass(frozen=True, slots=True)
class SmoothEffect:
    """Smooth signal with moving average.

    Args:
        window: Moving average window size in steps
    """

    window: int


@dataclass(frozen=True, slots=True)
class InvertEffect:
    """Invert signal polarity (multiply by -1)."""

    pass


@dataclass(frozen=True, slots=True)
class AbsEffect:
    """Take absolute value of signal."""

    pass


@dataclass(frozen=True, slots=True)
class FoldEffect:
    """Fold signal at threshold (waveshaping).

    When signal exceeds threshold, it folds back.

    Args:
        threshold: Fold threshold (0.0 to 1.0)
    """

    threshold: float = 1.0


@dataclass(frozen=True, slots=True)
class WrapEffect:
    """Wrap signal around range (modulo-style).

    Args:
        min_val: Minimum value
        max_val: Maximum value
    """

    min_val: float = -1.0
    max_val: float = 1.0


@dataclass(frozen=True, slots=True)
class PowerEffect:
    """Apply power curve (for exponential/log shaping).

    Args:
        exponent: Power exponent (>1 = curve up, <1 = curve down)
    """

    exponent: float


@dataclass(frozen=True, slots=True)
class SliceEffect:
    """Time-slice the signal (sample & hold style).

    Args:
        steps: Hold each value for N steps
    """

    steps: int


@dataclass(frozen=True, slots=True)
class MixEffect:
    """Mix another signal expression.

    Args:
        other: Another SignalExpr to mix
        amount: Mix amount (0.0 = self only, 1.0 = other only)
    """

    other: "SignalExpr"
    amount: float = 0.5


@dataclass(frozen=True, slots=True)
class MultiplyEffect:
    """Multiply (ring modulate) with another signal.

    Args:
        other: Another SignalExpr to multiply with
    """

    other: "SignalExpr"


# Union of all signal effect types
SignalEffect = Union[
    ClipEffect,
    ScaleEffect,
    OffsetEffect,
    AddNoiseEffect,
    QuantizeEffect,
    SmoothEffect,
    InvertEffect,
    AbsEffect,
    FoldEffect,
    WrapEffect,
    PowerEffect,
    SliceEffect,
    MixEffect,
    MultiplyEffect,
]


# =============================================================================
# SignalExpr - Complete signal expression
# =============================================================================


@dataclass(frozen=True, slots=True)
class SignalExpr:
    """Signal expression: source + effect chain.

    Immutable representation of a signal processing chain.
    Use pipe() to build chains fluently.

    Example:
        expr = SignalExpr(LfoSource("sin", cycles=4))
        expr = expr.pipe(AddNoiseEffect(0.1)).pipe(ClipEffect(-0.8, 0.8))
    """

    source: SignalSource
    effects: tuple[SignalEffect, ...] = ()

    def pipe(self, effect: SignalEffect) -> SignalExpr:
        """Add effect to chain, returning new SignalExpr.

        Args:
            effect: Effect to add

        Returns:
            New SignalExpr with effect appended
        """
        return SignalExpr(
            source=self.source,
            effects=self.effects + (effect,),
        )

    def __or__(self, effect: SignalEffect) -> SignalExpr:
        """Operator overload for pipe: expr | effect."""
        return self.pipe(effect)


# =============================================================================
# Convenience constructors
# =============================================================================


def sin(cycles: float, amount: float = 1.0, phase: float = 0.0) -> SignalExpr:
    """Create sine LFO expression."""
    return SignalExpr(LfoSource("sin", cycles, amount, phase))


def tri(cycles: float, amount: float = 1.0, phase: float = 0.0) -> SignalExpr:
    """Create triangle LFO expression."""
    return SignalExpr(LfoSource("tri", cycles, amount, phase))


def saw(cycles: float, amount: float = 1.0, phase: float = 0.0) -> SignalExpr:
    """Create sawtooth LFO expression."""
    return SignalExpr(LfoSource("saw", cycles, amount, phase))


def square(cycles: float, amount: float = 1.0, phase: float = 0.0) -> SignalExpr:
    """Create square LFO expression."""
    return SignalExpr(LfoSource("square", cycles, amount, phase))


def noise(amount: float = 1.0, seed: int | None = None) -> SignalExpr:
    """Create random noise expression."""
    return SignalExpr(RandomSource(seed, amount))


def env(
    attack: int = 16, hold: int = 32, release: int = 48, amount: float = 1.0
) -> SignalExpr:
    """Create envelope expression."""
    return SignalExpr(EnvelopeSource(attack, hold, release, amount))


def steps(values: list[float], steps_per_value: int = 16) -> SignalExpr:
    """Create step sequence expression."""
    return SignalExpr(StepSequenceSource(tuple(values), steps_per_value))


def const(value: float) -> SignalExpr:
    """Create constant value expression."""
    return SignalExpr(ConstantSource(value))
