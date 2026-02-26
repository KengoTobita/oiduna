"""
OSC protocol validator.

Validates OSC messages according to OSC 1.0 specification.
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
