"""
Command result type for error handling.

Provides a standardized way to return success/failure status from command handlers.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class CommandResult:
    """
    Result of a command execution.

    Attributes:
        success: True if command succeeded, False otherwise
        message: Optional error or success message
        data: Optional result data
    """

    success: bool
    message: str | None = None
    data: dict[str, Any] | None = None

    @classmethod
    def ok(cls, message: str | None = None, data: dict[str, Any] | None = None) -> "CommandResult":
        """
        Create a successful result.

        Args:
            message: Optional success message
            data: Optional result data

        Returns:
            CommandResult with success=True
        """
        return cls(success=True, message=message, data=data)

    @classmethod
    def error(cls, message: str, data: dict[str, Any] | None = None) -> "CommandResult":
        """
        Create an error result.

        Args:
            message: Error message
            data: Optional error data

        Returns:
            CommandResult with success=False
        """
        return cls(success=False, message=message, data=data)
