"""Constants for Oiduna Loop Engine.

Includes:
- Step-related constants (256-step loop)
- MIDI CC constants and aliases
"""

from __future__ import annotations

from typing import Final

# =============================================================================
# Step-related constants
# =============================================================================

# Core loop length - fixed at 256 steps
LOOP_STEPS: Final[int] = 256

# Timing subdivisions
STEPS_PER_BEAT: Final[int] = 4  # 16th note per beat (4 beats per bar)
STEPS_PER_BAR: Final[int] = 16  # 16 steps per bar (1 bar = 4 beats)

# =============================================================================
# MIDI-related constants
# =============================================================================

# Standard MIDI CC numbers
CC_MODWHEEL: Final[int] = 1
CC_BREATH: Final[int] = 2
CC_VOLUME: Final[int] = 7
CC_PAN: Final[int] = 10
CC_EXPRESSION: Final[int] = 11
CC_SUSTAIN: Final[int] = 64

# Synth-specific CC numbers (commonly used)
CC_CUTOFF: Final[int] = 74
CC_RESONANCE: Final[int] = 71

# =============================================================================
# CC Aliases for DSL Modulation Targets
# =============================================================================

CC_ALIASES: Final[dict[str, int]] = {
    # Expression controllers
    "modwheel": 1,
    "mod": 1,
    "breath": 2,
    "foot": 4,
    "portamento_time": 5,
    "volume": 7,
    "balance": 8,
    "pan": 10,
    "expression": 11,
    # Bank select
    "bank_msb": 0,
    "bank_lsb": 32,
    # Effects depth (General MIDI)
    "fx1_depth": 91,  # Reverb
    "fx2_depth": 92,  # Tremolo
    "fx3_depth": 93,  # Chorus
    "fx4_depth": 94,  # Detune
    "fx5_depth": 95,  # Phaser
    # Sound controllers
    "resonance": 71,
    "release": 72,
    "attack": 73,
    "cutoff": 74,
    "brightness": 74,
    "decay": 75,
    "vibrato_rate": 76,
    "vibrato_depth": 77,
    "vibrato_delay": 78,
    # Switches
    "sustain": 64,
    "hold": 64,
    "portamento": 65,
    "sostenuto": 66,
    "soft": 67,
    "legato": 68,
    "hold2": 69,
}

# Special MIDI modulation targets (not CC numbers)
SPECIAL_MIDI_TARGETS: Final[frozenset[str]] = frozenset({
    "pitch_bend",
    "aftertouch",
    "velocity",
})


def resolve_cc_target(target: str) -> int | None:
    """
    Resolve CC target string to CC number.

    Handles both numeric and named CC targets:
    - "cc.74" -> 74
    - "cc.cutoff" -> 74
    - "cutoff" -> 74 (without cc. prefix)

    Args:
        target: CC target string (e.g., "cc.74", "cc.cutoff", "cutoff")

    Returns:
        CC number (0-127) or None if invalid/unknown
    """
    # Strip "cc." prefix if present
    if target.startswith("cc."):
        target = target[3:]

    # Try numeric first
    if target.isdigit():
        num = int(target)
        return num if 0 <= num <= 127 else None

    # Try alias lookup (case-insensitive)
    return CC_ALIASES.get(target.lower())


def is_special_midi_target(target: str) -> bool:
    """
    Check if target is a special MIDI message (not CC).

    Args:
        target: Target string

    Returns:
        True if target is pitch_bend, aftertouch, or velocity
    """
    return target in SPECIAL_MIDI_TARGETS
