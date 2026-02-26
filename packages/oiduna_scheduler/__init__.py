"""
Scheduler package for Oiduna.

Handles message scheduling and routing to destinations.
Uses lightweight dataclasses for runtime performance.
"""

from scheduler_models import (
    ScheduledMessage,
    ScheduledMessageBatch,
)
from scheduler import MessageScheduler
from router import DestinationRouter
from senders import OscDestinationSender, MidiDestinationSender

__all__ = [
    "ScheduledMessage",
    "ScheduledMessageBatch",
    "MessageScheduler",
    "DestinationRouter",
    "OscDestinationSender",
    "MidiDestinationSender",
]
