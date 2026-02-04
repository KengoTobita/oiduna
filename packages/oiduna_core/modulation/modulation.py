"""Modulation models for Oiduna Framework.

Defines modulation types, parameter specifications, and the Modulation class.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .step_buffer import StepBuffer


class ModulationType(Enum):
    """Modulation application method.

    Determines how the signal value is applied to the base parameter.
    """

    ADDITIVE = "additive"  # base + signal * range
    MULTIPLICATIVE = "mult"  # base * (1 + signal)
    BIPOLAR = "bipolar"  # center + signal * half_range


@dataclass(frozen=True)
class ParamSpec:
    """Parameter specification for modulation.

    Defines the valid range and modulation type for a parameter.
    """

    name: str
    min_value: float
    max_value: float
    default: float
    mod_type: ModulationType


# Parameter specifications table
PARAM_SPECS: dict[str, ParamSpec] = {
    # Sound params
    "gain": ParamSpec("gain", 0.0, 2.0, 1.0, ModulationType.MULTIPLICATIVE),
    "pan": ParamSpec("pan", 0.0, 1.0, 0.5, ModulationType.BIPOLAR),
    "speed": ParamSpec("speed", 0.1, 4.0, 1.0, ModulationType.MULTIPLICATIVE),
    # Filter
    "cutoff": ParamSpec(
        "cutoff", 20.0, 20000.0, 1000.0, ModulationType.MULTIPLICATIVE
    ),
    "resonance": ParamSpec("resonance", 0.0, 1.0, 0.0, ModulationType.ADDITIVE),
    "hcutoff": ParamSpec(
        "hcutoff", 20.0, 20000.0, 5000.0, ModulationType.MULTIPLICATIVE
    ),
    "hresonance": ParamSpec("hresonance", 0.0, 1.0, 0.0, ModulationType.ADDITIVE),
    # Reverb
    "room": ParamSpec("room", 0.0, 1.0, 0.0, ModulationType.ADDITIVE),
    "size": ParamSpec("size", 0.0, 1.0, 0.5, ModulationType.ADDITIVE),
    "dry": ParamSpec("dry", 0.0, 1.0, 1.0, ModulationType.ADDITIVE),
    # Delay
    "delay_send": ParamSpec("delay_send", 0.0, 1.0, 0.0, ModulationType.ADDITIVE),
    "delay_time": ParamSpec("delay_time", 0.0, 2.0, 0.0, ModulationType.ADDITIVE),
    "delay_feedback": ParamSpec(
        "delay_feedback", 0.0, 1.0, 0.0, ModulationType.ADDITIVE
    ),
    # Distortion
    "shape": ParamSpec("shape", 0.0, 1.0, 0.0, ModulationType.ADDITIVE),
    "crush": ParamSpec("crush", 1.0, 16.0, 16.0, ModulationType.ADDITIVE),
    # Envelope
    "attack": ParamSpec("attack", 0.0, 2.0, 0.001, ModulationType.ADDITIVE),
    "hold": ParamSpec("hold", 0.0, 2.0, 0.0, ModulationType.ADDITIVE),
    "release": ParamSpec("release", 0.0, 2.0, 0.2, ModulationType.ADDITIVE),
}


@dataclass(frozen=True)
class Modulation:
    """Modulation definition.

    Connects a signal (StepBuffer) to a target parameter.
    """

    target_param: str
    signal: StepBuffer

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "target_param": self.target_param,
            "signal": self.signal.to_list(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Modulation:
        """Create from dictionary (deserialization)."""
        return cls(
            target_param=data["target_param"],
            signal=StepBuffer.from_list(data["signal"]),
        )


def apply_modulation(
    base_value: float,
    signal_value: float,
    spec: ParamSpec,
) -> float:
    """
    Apply modulation to a base parameter value.

    Args:
        base_value: The base parameter value
        signal_value: Signal value (-1.0 to +1.0)
        spec: Parameter specification

    Returns:
        Modulated value (clamped to valid range)
    """
    match spec.mod_type:
        case ModulationType.ADDITIVE:
            range_size = spec.max_value - spec.min_value
            result = base_value + signal_value * range_size

        case ModulationType.MULTIPLICATIVE:
            factor = 1.0 + signal_value
            result = base_value * factor

        case ModulationType.BIPOLAR:
            half_range = (spec.max_value - spec.min_value) / 2
            result = base_value + signal_value * half_range

    return max(spec.min_value, min(spec.max_value, result))
