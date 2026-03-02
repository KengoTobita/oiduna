"""Session manager components."""

from .base import BaseManager, SessionEventSink, EventSink  # EventSink is legacy alias
from .client_manager import ClientManager
from .destination_manager import DestinationManager
from .environment_manager import EnvironmentManager
from .track_manager import TrackManager
from .pattern_manager import PatternManager

__all__ = [
    "BaseManager",
    "SessionEventSink",
    "EventSink",  # Legacy alias (deprecated)
    "ClientManager",
    "DestinationManager",
    "EnvironmentManager",
    "TrackManager",
    "PatternManager",
]
