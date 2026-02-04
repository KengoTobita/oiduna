"""Modulation models for Oiduna Framework."""

from .modulation import (
    PARAM_SPECS,
    Modulation,
    ModulationType,
    ParamSpec,
    apply_modulation,
)
from .signal_expr import (
    SignalExpr,
    SignalSource,
    SignalEffect,
)
from .step_buffer import StepBuffer

__all__ = [
    "Modulation",
    "ModulationType",
    "ParamSpec",
    "PARAM_SPECS",
    "apply_modulation",
    "SignalExpr",
    "SignalSource",
    "SignalEffect",
    "StepBuffer",
]
