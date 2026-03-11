"""Oiduna client library - Python client for Oiduna API

Example:
    >>> from oiduna.interface.client import OidunaClient
    >>> async with OidunaClient() as client:
    ...     health = await client.health.check()
    ...     print(f"Status: {health.status}")
"""

from oiduna.interface.client.client import OidunaClient
from oiduna.interface.client.exceptions import (
    OidunaError,
    OidunaAPIError,
    ValidationError,
    TimeoutError,
)

__version__ = "0.1.0"

__all__ = [
    "OidunaClient",
    "OidunaError",
    "OidunaAPIError",
    "ValidationError",
    "TimeoutError",
]
