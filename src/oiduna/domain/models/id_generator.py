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
        # Ensures uniqueness within session
        self._track_ids: Set[str] = set()
        self._pattern_ids: Set[str] = set()

    def _generate_unique_id(
        self,
        id_pool: Set[str],
        id_type: str,
        byte_length: int = 2
    ) -> str:
        """
        Generate a unique hexadecimal ID with collision detection.

        Template Method: Defines the algorithm skeleton for ID generation,
        with specific ID pools and types passed as parameters.

        Args:
            id_pool: Set to check for uniqueness and store generated IDs
            id_type: Type of ID for error messages (e.g., 'track_id', 'pattern_id')
            byte_length: Number of bytes (2 bytes = 4 hex chars, 4 bytes = 8 hex chars)

        Returns:
            Unique hexadecimal ID string

        Raises:
            RuntimeError: If unable to generate unique ID after max attempts

        Example:
            >>> gen = IDGenerator()
            >>> id = gen._generate_unique_id(gen._track_ids, "track_id")
            >>> len(id)
            4
        """
        max_attempts = 100
        for _ in range(max_attempts):
            new_id = secrets.token_hex(byte_length)
            if new_id not in id_pool:
                id_pool.add(new_id)
                return new_id
        raise RuntimeError(
            f"Failed to generate unique {id_type} after {max_attempts} attempts"
        )

    def generate_track_id(self) -> str:
        """
        Generate unique track_id within this session.

        Returns:
            4-digit hexadecimal string (e.g., '0a1f')

        Raises:
            RuntimeError: If unable to generate unique ID after 100 attempts
        """
        return self._generate_unique_id(self._track_ids, "track_id")

    def generate_pattern_id(self) -> str:
        """
        Generate unique pattern_id within this session.

        Returns:
            4-digit hexadecimal string (e.g., '3e2b')

        Raises:
            RuntimeError: If unable to generate unique ID after 100 attempts
        """
        return self._generate_unique_id(self._pattern_ids, "pattern_id")

    def reset(self) -> None:
        """Reset all ID pools (for testing)."""
        self._track_ids.clear()
        self._pattern_ids.clear()
