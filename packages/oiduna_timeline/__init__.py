"""
Oiduna Timeline Scheduling Package.

Provides timeline-based scheduling for pattern changes,
enabling multi-loop-ahead reservations.
"""

from .models import ScheduledChange
from .timeline import ScheduledChangeTimeline
from .merger import merge_changes

__all__ = [
    "ScheduledChange",
    "ScheduledChangeTimeline",
    "merge_changes",
]
