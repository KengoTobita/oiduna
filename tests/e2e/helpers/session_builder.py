"""Fluent API for building test session data."""

from __future__ import annotations

from typing import Any


class SessionBuilder:
    """Fluent API for building test session data programmatically."""

    def __init__(self):
        """Initialize session builder with defaults."""
        self._bpm: float = 120.0
        self._pattern_length: float = 4.0
        self._messages: list[dict[str, Any]] = []
        self._tracks: list[dict[str, Any]] = []
        self._patterns: list[dict[str, Any]] = []

    def with_bpm(self, bpm: float) -> SessionBuilder:
        """Set BPM.

        Args:
            bpm: Beats per minute

        Returns:
            Self for chaining
        """
        self._bpm = bpm
        return self

    def with_pattern_length(self, pattern_length: float) -> SessionBuilder:
        """Set pattern length in bars.

        Args:
            pattern_length: Pattern length in bars

        Returns:
            Self for chaining
        """
        self._pattern_length = pattern_length
        return self

    def add_message(
        self,
        destination_id: str,
        step: int,
        offset: float = 0.0,
        params: dict[str, Any] | None = None,
    ) -> SessionBuilder:
        """Add a message to the session.

        Args:
            destination_id: Destination ID
            step: Step number (0-255)
            offset: Offset value (0.0-1.0)
            params: Message parameters

        Returns:
            Self for chaining
        """
        self._messages.append({
            "destination_id": destination_id,
            "step": step,
            "offset": offset,
            "params": params or {},
        })
        return self

    def add_kick_pattern(
        self,
        steps: list[int],
        destination_id: str = "osc_default",
        gain: float = 0.8,
    ) -> SessionBuilder:
        """Add a kick drum pattern.

        Args:
            steps: List of step numbers for kicks
            destination_id: Destination ID
            gain: Gain value (0.0-1.0)

        Returns:
            Self for chaining
        """
        for step in steps:
            self.add_message(
                destination_id=destination_id,
                step=step,
                params={"s": "bd", "gain": gain},
            )
        return self

    def add_hihat_pattern(
        self,
        steps: list[int],
        destination_id: str = "osc_default",
        gain: float = 0.6,
    ) -> SessionBuilder:
        """Add a hi-hat pattern.

        Args:
            steps: List of step numbers for hi-hats
            destination_id: Destination ID
            gain: Gain value (0.0-1.0)

        Returns:
            Self for chaining
        """
        for step in steps:
            self.add_message(
                destination_id=destination_id,
                step=step,
                params={"s": "hh", "gain": gain},
            )
        return self

    def add_dense_pattern(
        self,
        num_messages: int,
        destination_id: str = "osc_default",
        track_id: str = "track1",
    ) -> SessionBuilder:
        """Add a dense pattern with many messages.

        Args:
            num_messages: Number of messages to add
            destination_id: Destination ID
            track_id: Track ID

        Returns:
            Self for chaining
        """
        for i in range(num_messages):
            step = (i * 256 // num_messages) % 256
            self.add_message(
                destination_id=destination_id,
                step=step,
                params={"s": f"sound{i % 10}", "note": i % 128},
            )
        return self

    def build(self) -> dict[str, Any]:
        """Build the session data.

        Returns:
            Session data dictionary
        """
        return {
            "bpm": self._bpm,
            "pattern_length": self._pattern_length,
            "messages": self._messages,
            "tracks": self._tracks,
            "patterns": self._patterns,
        }
