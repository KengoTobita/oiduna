"""
Oiduna Timeline Scheduling Package.

Provides timeline-based scheduling for pattern changes,
enabling multi-loop-ahead reservations.
"""

from .models import CuedChange
from .timeline import CuedChangeTimeline
from .merger import merge_changes

__all__ = [
    "CuedChange",
    "CuedChangeTimeline",
    "merge_changes",
]
