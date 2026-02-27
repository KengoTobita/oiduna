"""
Sequential ID generator for tracks and patterns.

Generates human-readable IDs like track_001, pattern_001.
"""

from typing import Literal


class IDGenerator:
    """
    Generate sequential IDs for tracks and patterns.

    IDs are formatted as {prefix}_{counter:03d}:
    - track_001, track_002, ...
    - pattern_001, pattern_002, ...

    Example:
        >>> gen = IDGenerator()
        >>> gen.next_track_id()
        'track_001'
        >>> gen.next_track_id()
        'track_002'
        >>> gen.next_pattern_id()
        'pattern_001'
    """

    def __init__(self):
        self._track_counter = 0
        self._pattern_counter = 0

    def next_track_id(self) -> str:
        """Generate next track ID (track_001, track_002, ...)."""
        self._track_counter += 1
        return f"track_{self._track_counter:03d}"

    def next_pattern_id(self) -> str:
        """Generate next pattern ID (pattern_001, pattern_002, ...)."""
        self._pattern_counter += 1
        return f"pattern_{self._pattern_counter:03d}"

    def reset(self) -> None:
        """Reset counters (for testing or session reset)."""
        self._track_counter = 0
        self._pattern_counter = 0
