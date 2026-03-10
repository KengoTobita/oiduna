"""
Session-scoped 4-digit hexadecimal ID generator with collision checking.

Generates unique IDs like '0a1f' for tracks and patterns within a session.
"""

import secrets
from typing import Set


class IDGenerator:
    """
    Generate 4-digit hexadecimal IDs with collision checking.

    IDs are unique within a session:
    - track_id: 0a1f (4-digit hex)
    - pattern_id: 3e2b (4-digit hex)

    Note: session_id (8-digit) is generated directly by Session class.

    Example:
        >>> gen = IDGenerator()
        >>> track_id = gen.generate_track_id()
        >>> len(track_id)
        4
        >>> all(c in '0123456789abcdef' for c in track_id)
        True
    """

    def __init__(self) -> None:
        # Session内で一意性を保証
        self._track_ids: Set[str] = set()
        self._pattern_ids: Set[str] = set()

    def generate_track_id(self) -> str:
        """
        Generate unique track_id within this session.

        Returns:
            4-digit hexadecimal string (e.g., '0a1f')

        Raises:
            RuntimeError: If unable to generate unique ID after 100 attempts
        """
        max_attempts = 100
        for _ in range(max_attempts):
            new_id = secrets.token_hex(2)  # 4-digit hex (2 bytes = 4 hex chars)
            if new_id not in self._track_ids:
                self._track_ids.add(new_id)
                return new_id
        raise RuntimeError(f"Failed to generate unique track_id after {max_attempts} attempts")

    def generate_pattern_id(self) -> str:
        """
        Generate unique pattern_id within this session.

        Returns:
            4-digit hexadecimal string (e.g., '3e2b')

        Raises:
            RuntimeError: If unable to generate unique ID after 100 attempts
        """
        max_attempts = 100
        for _ in range(max_attempts):
            new_id = secrets.token_hex(2)  # 4-digit hex (2 bytes = 4 hex chars)
            if new_id not in self._pattern_ids:
                self._pattern_ids.add(new_id)
                return new_id
        raise RuntimeError(f"Failed to generate unique pattern_id after {max_attempts} attempts")

    def reset(self) -> None:
        """Reset all ID pools (for testing)."""
        self._track_ids.clear()
        self._pattern_ids.clear()
