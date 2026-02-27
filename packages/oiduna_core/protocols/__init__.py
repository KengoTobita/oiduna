"""
Protocol interfaces for oiduna_core.

This module exports protocol definitions for:
- IPC communication (CommandSource, StateSink)
"""

from oiduna_core.protocols.ipc import CommandSink, CommandSource, StateSink, StateSource

__all__ = [
    # IPC protocols
    "CommandSink",
    "CommandSource",
    "StateSink",
    "StateSource",
]
