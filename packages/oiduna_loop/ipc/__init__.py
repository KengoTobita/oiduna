"""Oiduna Loop IPC — in-process implementations."""

from .in_process import InProcessStateSink, NoopCommandSource

__all__ = ["NoopCommandSource", "InProcessStateSink"]
