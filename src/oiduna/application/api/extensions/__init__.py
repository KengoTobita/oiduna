"""Oiduna API extension system.

Provides a plugin architecture for session transformation and runtime hooks.
"""

from .base import BaseExtension
from .pipeline import ExtensionPipeline, ExtensionError, discover_extensions

__all__ = [
    "BaseExtension",
    "ExtensionPipeline",
    "ExtensionError",
    "discover_extensions",
]
