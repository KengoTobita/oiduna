"""Common validation functions for domain models.

This module provides reusable validation functions to eliminate code duplication
across model field validators.
"""


def validate_hexadecimal_id(
    value: str,
    length: int,
    field_name: str
) -> str:
    """
    Validate hexadecimal ID format.

    Args:
        value: The ID string to validate
        length: Expected length (e.g., 4 for track_id/pattern_id, 8 for session_id)
        field_name: Name of the field for error messages

    Returns:
        The validated ID string (lowercase hexadecimal)

    Raises:
        ValueError: If ID doesn't match expected hexadecimal format

    Example:
        >>> validate_hexadecimal_id("0a1f", 4, "track_id")
        '0a1f'
        >>> validate_hexadecimal_id("ABCD", 4, "pattern_id")
        'abcd'
        >>> validate_hexadecimal_id("xyz", 4, "track_id")
        Traceback (most recent call last):
            ...
        ValueError: track_id must be 4-digit hexadecimal (e.g., '0a1f'). Got: 'xyz'
    """
    if not (len(value) == length and all(c in "0123456789abcdef" for c in value)):
        # Generate example based on length
        example = "0a1f" if length == 4 else "a1b2c3d4"
        raise ValueError(
            f"{field_name} must be {length}-digit hexadecimal "
            f"(e.g., '{example}'). "
            f"Got: '{value}'"
        )
    return value
