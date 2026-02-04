"""Step-related constants for Oiduna Framework.

The 256-step loop is a core product concept and is fixed.
"""

from typing import Final

# Core loop length - fixed at 256 steps
LOOP_STEPS: Final[int] = 256

# Timing subdivisions
STEPS_PER_BEAT: Final[int] = 4  # 16th note per beat (4 beats per bar)
STEPS_PER_BAR: Final[int] = 16  # 16 steps per bar (1 bar = 4 beats)
