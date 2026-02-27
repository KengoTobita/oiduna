"""
Scheduler package for Oiduna.

Handles message scheduling and routing to destinations.
Uses lightweight dataclasses for runtime performance.
"""

from oiduna_scheduler.scheduler_models import (
    ScheduledMessage,
    ScheduledMessageBatch,
)
from oiduna_scheduler.scheduler import MessageScheduler
from oiduna_scheduler.router import DestinationRouter
from oiduna_scheduler.senders import OscDestinationSender, MidiDestinationSender

__all__ = [
    "ScheduledMessage",
    "ScheduledMessageBatch",
    "MessageScheduler",
    "DestinationRouter",
    "OscDestinationSender",
    "MidiDestinationSender",
]
