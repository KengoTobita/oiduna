"""
Session management package for Oiduna.

Provides:
- SessionContainer: Lightweight manager container
- SessionValidator: Business logic validation
"""

from .container import SessionContainer
from .validator import SessionValidator

__all__ = [
    "SessionContainer",
    "SessionValidator",
]
