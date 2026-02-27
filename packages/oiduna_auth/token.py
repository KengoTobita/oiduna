"""
Token generation and validation utilities.

Uses UUID4 for simple, stateless authentication tokens.
"""

import uuid


def generate_token() -> str:
    """
    Generate a new UUID4 authentication token.

    Returns:
        A UUID4 string (e.g., "550e8400-e29b-41d4-a716-446655440000")

    Example:
        >>> token = generate_token()
        >>> len(token)
        36
        >>> validate_token(token)
        True
    """
    return str(uuid.uuid4())


def validate_token(token: str) -> bool:
    """
    Validate that a token is a valid UUID4.

    Args:
        token: Token string to validate

    Returns:
        True if valid UUID4, False otherwise

    Example:
        >>> validate_token("550e8400-e29b-41d4-a716-446655440000")
        True
        >>> validate_token("invalid-token")
        False
    """
    try:
        uuid.UUID(token, version=4)
        return True
    except (ValueError, AttributeError):
        return False
