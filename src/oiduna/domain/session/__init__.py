"""
Session management package for Oiduna.

Provides:
- SessionContainer: Repository/Service container
- SessionValidator: Business logic validation
- SessionChangePublisher: Protocol for SSE event publishing
"""

from .container import SessionContainer
from .validator import SessionValidator
from .types import SessionChangePublisher

__all__ = [
    "SessionContainer",
    "SessionValidator",
    "SessionChangePublisher",
]
