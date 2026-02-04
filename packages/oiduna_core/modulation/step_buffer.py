"""StepBuffer - 256-step fixed-length immutable buffer.

Used for Signal values and other step-based data in Oiduna Framework.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Sequence

from oiduna_core.constants.steps import LOOP_STEPS


@dataclass(frozen=True, slots=True)
class StepBuffer:
    """
    256-step fixed-length immutable numeric buffer.

    The 256-step loop is a core product concept, so this type
    enforces the constraint rather than using a plain list.

    Attributes:
        _data: Internal tuple of float values (exactly 256 elements)
    """

    _data: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self._data) != LOOP_STEPS:
            raise ValueError(
                f"StepBuffer requires exactly {LOOP_STEPS} values, "
                f"got {len(self._data)}"
            )

    # ===== Factory Methods =====

    @classmethod
    def from_sequence(cls, values: Sequence[float]) -> StepBuffer:
        """Create StepBuffer from a sequence."""
        return cls(_data=tuple(values))

    @classmethod
    def fill(cls, value: float = 0.0) -> StepBuffer:
        """Create StepBuffer filled with a single value."""
        return cls(_data=tuple([value] * LOOP_STEPS))

    @classmethod
    def from_list(cls, values: list[float]) -> StepBuffer:
        """Create from list (for deserialization)."""
        return cls(_data=tuple(values))

    # ===== Access =====

    def __getitem__(self, step: int) -> float:
        return self._data[step]

    def __len__(self) -> int:
        return int(LOOP_STEPS)

    def __iter__(self) -> Iterator[float]:
        return iter(self._data)

    # ===== Signal Operations =====

    def scale(self, factor: float) -> StepBuffer:
        """Scale all values by a factor (e.g., for amount application)."""
        return StepBuffer(_data=tuple(v * factor for v in self._data))

    def add(self, other: StepBuffer) -> StepBuffer:
        """Add two signals element-wise."""
        return StepBuffer(
            _data=tuple(a + b for a, b in zip(self._data, other._data))
        )

    def __add__(self, other: StepBuffer) -> StepBuffer:
        return self.add(other)

    def offset(self, value: float) -> StepBuffer:
        """Add a constant offset to all values."""
        return StepBuffer(_data=tuple(v + value for v in self._data))

    def clamp(self, min_val: float = -1.0, max_val: float = 1.0) -> StepBuffer:
        """Clamp all values to the specified range."""
        return StepBuffer(
            _data=tuple(max(min_val, min(max_val, v)) for v in self._data)
        )

    def lerp(self, other: StepBuffer, t: float) -> StepBuffer:
        """Linear interpolation between two buffers."""
        return StepBuffer(
            _data=tuple(a + (b - a) * t for a, b in zip(self._data, other._data))
        )

    # ===== Serialization =====

    def to_list(self) -> list[float]:
        """Convert to list (for serialization)."""
        return list(self._data)

    def __repr__(self) -> str:
        preview = list(self._data[:4])
        return f"StepBuffer({preview}... len={LOOP_STEPS})"
