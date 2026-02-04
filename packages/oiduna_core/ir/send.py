"""Send model for MARS DSL v5.

Represents a send/return routing from a Track to a MixerLine.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Send:
    """Send routing from a Track to a MixerLine.

    Attributes:
        target: The name of the target MixerLine
        amount: Send level (0.0 - 1.0)
    """

    target: str
    amount: float = 0.0

    def __post_init__(self) -> None:
        """Validate amount is in valid range."""
        if not 0.0 <= self.amount <= 1.0:
            object.__setattr__(
                self, "amount", max(0.0, min(1.0, self.amount))
            )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "target": self.target,
            "amount": self.amount,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Send:
        """Create from dictionary (deserialization)."""
        return cls(
            target=data["target"],
            amount=data.get("amount", 0.0),
        )
