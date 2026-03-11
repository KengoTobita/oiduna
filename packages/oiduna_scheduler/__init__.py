"""
Scheduler package for Oiduna.

Handles loop schedule execution and routing to destinations.
Uses lightweight dataclasses for runtime performance.
"""

from oiduna_scheduler.scheduler_models import (
    ScheduleEntry,
    LoopSchedule,
)
from oiduna_scheduler.scheduler import LoopScheduler
from oiduna_scheduler.router import DestinationRouter
from oiduna_scheduler.senders import OscDestinationSender, MidiDestinationSender

__all__ = [
    # Loop schedule execution
    "ScheduleEntry",
    "LoopSchedule",
    "LoopScheduler",
    # Infrastructure
    "DestinationRouter",
    "OscDestinationSender",
    "MidiDestinationSender",
]
