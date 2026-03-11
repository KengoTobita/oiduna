"""
Protocol validators for OSC and MIDI message validation.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass
class OscValidationResult:
    """Result of OSC message validation."""

    is_valid: bool
    errors: list[str]

    @staticmethod
    def success() -> OscValidationResult:
        """Create a successful validation result."""
        return OscValidationResult(is_valid=True, errors=[])

    @staticmethod
    def failure(errors: list[str]) -> OscValidationResult:
        """Create a failed validation result."""
        return OscValidationResult(is_valid=False, errors=errors)


@dataclass
class MidiValidationResult:
    """Result of MIDI message validation."""

    is_valid: bool
    errors: list[str]

    @staticmethod
    def success() -> MidiValidationResult:
        """Create a successful validation result."""
        return MidiValidationResult(is_valid=True, errors=[])

    @staticmethod
    def failure(errors: list[str]) -> MidiValidationResult:
        """Create a failed validation result."""
        return MidiValidationResult(is_valid=False, errors=errors)


class OscValidator:
    """
    Validates OSC messages for protocol compliance.

    OSC type tags:
    - i: int32
    - f: float32
    - s: string
    - b: blob (bytes)

    Design:
    - Content-agnostic: doesn't interpret params semantics
    - Protocol-focused: checks OSC spec compliance
    - Non-blocking: returns errors, doesn't raise exceptions
    """

    # OSC valid type tags
    VALID_TYPE_TAGS = {"i", "f", "s", "b"}

    def validate_message(self, params: dict[str, Any]) -> OscValidationResult:
        """
        Validate an OSC message parameter dictionary.

        Args:
            params: Message parameters (e.g., {"s": "bd", "gain": 0.8})

        Returns:
            OscValidationResult with validation status and errors

        Example:
            >>> validator = OscValidator()
            >>> result = validator.validate_message({"s": "bd", "gain": 0.8})
            >>> result.is_valid
            True
        """
        errors = []

        if not params:
            # Empty params is valid (rare but allowed)
            return OscValidationResult.success()

        # Check each parameter
        for key, value in params.items():
            # Validate key (OSC address pattern component)
            key_errors = self._validate_key(key)
            errors.extend(key_errors)

            # Validate value type
            value_errors = self._validate_value(key, value)
            errors.extend(value_errors)

        if errors:
            return OscValidationResult.failure(errors)
        return OscValidationResult.success()

    def _validate_key(self, key: str) -> list[str]:
        """
        Validate OSC parameter key.

        OSC keys should:
        - Be non-empty strings
        - Not contain spaces
        - Not contain special chars that break OSC address patterns

        Note: We're lenient here - SuperDirt uses camelCase keys
        """
        errors = []

        if not key:
            errors.append("Parameter key cannot be empty")
            return errors

        if not isinstance(key, str):
            errors.append(f"Parameter key must be string, got {type(key).__name__}")
            return errors

        # Check for problematic characters
        # OSC spec forbids: space, #, *, ,, ?, [, ], {, }
        forbidden_chars = {" ", "#", "*", ",", "?", "[", "]", "{", "}"}
        for char in forbidden_chars:
            if char in key:
                errors.append(f"Parameter key '{key}' contains forbidden character '{char}'")

        return errors

    def _validate_value(self, key: str, value: Any) -> list[str]:
        """
        Validate OSC parameter value.

        OSC supports:
        - int (i tag): 32-bit integers
        - float (f tag): 32-bit floats
        - str (s tag): strings
        - bytes (b tag): blobs

        Python types map naturally:
        - int → i
        - float → f
        - str → s
        - bytes → b
        """
        errors = []

        # Check type validity
        if isinstance(value, bool):
            # bool is subclass of int in Python, but OSC doesn't have bool
            # We allow it (converts to int 0/1)
            pass
        elif isinstance(value, int):
            # Check int32 range (-2^31 to 2^31-1)
            if value < -2147483648 or value > 2147483647:
                errors.append(f"Parameter '{key}' value {value} exceeds int32 range")
        elif isinstance(value, float):
            # Check finite
            if not (-3.4e38 <= value <= 3.4e38):
                errors.append(f"Parameter '{key}' value {value} exceeds float32 range")
        elif isinstance(value, str):
            # Strings are valid (no length limit in OSC spec)
            pass
        elif isinstance(value, bytes):
            # Blobs are valid
            pass
        elif isinstance(value, list):
            # Lists/arrays not directly supported in basic OSC
            # Some implementations support them, but we reject for strict compliance
            errors.append(f"Parameter '{key}' has list value (not supported in OSC 1.0)")
        elif isinstance(value, dict):
            # Dicts not supported
            errors.append(f"Parameter '{key}' has dict value (not supported in OSC)")
        elif value is None:
            # None/null not supported in basic OSC (some extensions have Nil/Null)
            errors.append(f"Parameter '{key}' has None value (not supported in OSC 1.0)")
        else:
            # Unknown type
            errors.append(
                f"Parameter '{key}' has unsupported type {type(value).__name__}"
            )

        return errors


class MidiValidator:
    """
    Validates MIDI messages for protocol compliance.

    MIDI 1.0 ranges:
    - Note numbers: 0-127
    - Velocity: 0-127 (0 = note off)
    - CC numbers: 0-127
    - CC values: 0-127
    - Channel: 0-15 (some systems use 1-16)
    - Program: 0-127

    Design:
    - Content-agnostic: doesn't interpret musical meaning
    - Protocol-focused: checks MIDI spec compliance
    - Non-blocking: returns errors, doesn't raise exceptions
    """

    def validate_message(self, params: dict[str, Any]) -> MidiValidationResult:
        """
        Validate a MIDI message parameter dictionary.

        Args:
            params: Message parameters (e.g., {"note": 60, "velocity": 100})

        Returns:
            MidiValidationResult with validation status and errors

        Example:
            >>> validator = MidiValidator()
            >>> result = validator.validate_message({"note": 60, "velocity": 100})
            >>> result.is_valid
            True
        """
        errors = []

        if not params:
            errors.append("MIDI message cannot have empty params")
            return MidiValidationResult.failure(errors)

        # Validate common MIDI parameters
        # Note: Different MIDI message types have different required fields
        # We do basic range checking for any MIDI param that appears

        # Note number (if present)
        if "note" in params:
            errors.extend(self._validate_range("note", params["note"], 0, 127))

        # Velocity (if present)
        if "velocity" in params:
            errors.extend(self._validate_range("velocity", params["velocity"], 0, 127))

        # Channel (if present)
        if "channel" in params:
            # Accept both 0-15 and 1-16 ranges
            channel = params["channel"]
            if isinstance(channel, int):
                if not (0 <= channel <= 15 or 1 <= channel <= 16):
                    errors.append(
                        f"Parameter 'channel' value {channel} outside valid range (0-15 or 1-16)"
                    )
            else:
                errors.append(
                    f"Parameter 'channel' must be int, got {type(channel).__name__}"
                )

        # Control Change number (if present)
        if "cc" in params:
            errors.extend(self._validate_range("cc", params["cc"], 0, 127))

        # Control Change value (if present)
        if "value" in params and "cc" in params:
            # 'value' is CC value when 'cc' is present
            errors.extend(self._validate_range("value", params["value"], 0, 127))

        # Program change (if present)
        if "program" in params:
            errors.extend(self._validate_range("program", params["program"], 0, 127))

        # Pitch bend (if present)
        if "pitch_bend" in params:
            # Pitch bend is 14-bit: 0-16383, center at 8192
            errors.extend(
                self._validate_range("pitch_bend", params["pitch_bend"], 0, 16383)
            )

        # Duration (if present) - not part of MIDI spec but commonly used
        if "duration_ms" in params:
            duration = params["duration_ms"]
            if not isinstance(duration, (int, float)):
                errors.append(
                    f"Parameter 'duration_ms' must be numeric, got {type(duration).__name__}"
                )
            elif duration < 0:
                errors.append(f"Parameter 'duration_ms' must be non-negative, got {duration}")

        if errors:
            return MidiValidationResult.failure(errors)
        return MidiValidationResult.success()

    def _validate_range(
        self, param_name: str, value: Any, min_val: int, max_val: int
    ) -> list[str]:
        """
        Validate that a parameter is an integer within range.

        Args:
            param_name: Parameter name (for error messages)
            value: Value to validate
            min_val: Minimum valid value (inclusive)
            max_val: Maximum valid value (inclusive)

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        if not isinstance(value, int):
            errors.append(
                f"Parameter '{param_name}' must be int, got {type(value).__name__}"
            )
            return errors

        if value < min_val or value > max_val:
            errors.append(
                f"Parameter '{param_name}' value {value} outside valid range ({min_val}-{max_val})"
            )

        return errors


__all__ = [
    "OscValidator",
    "OscValidationResult",
    "MidiValidator",
    "MidiValidationResult",
]
