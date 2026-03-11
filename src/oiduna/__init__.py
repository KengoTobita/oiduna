"""
Oiduna - Real-time SuperDirt/MIDI loop engine

A 4-layer architecture for real-time music performance:
- Domain: Business logic and models
- Infrastructure: Technical implementations
- Application: Use cases and services
- Interface: CLI and HTTP clients
"""

__version__ = "1.0.0"

# Domain models (most commonly used)
from .domain.models import (
    Session,
    Track,
    Pattern,
    PatternEvent,
    ClientInfo,
    Environment,
    StepNumber,
    BeatNumber,
    CycleFloat,
    BPM,
    Milliseconds,
    DestinationConfig,
    OscDestinationConfig,
    MidiDestinationConfig,
)

# Domain schedule
from .domain.schedule import (
    ScheduleEntry,
    LoopSchedule,
    SessionCompiler,
)

# Domain timeline
from .domain.timeline import (
    CuedChange,
    CuedChangeTimeline,
)

# Domain session
from .domain.session import (
    SessionContainer,
    SessionValidator,
)

# Infrastructure execution
from .infrastructure.execution import (
    LoopEngine,
)

# Infrastructure routing
from .infrastructure.routing import (
    DestinationRouter,
    LoopScheduler,
)

# Infrastructure transport
from .infrastructure.transport import (
    OscSender,
    MidiSender,
)

# Application
from .application.factory import create_loop_engine
from .application.api.main import app

__all__ = [
    # Version
    "__version__",

    # Domain models
    "Session",
    "Track",
    "Pattern",
    "PatternEvent",
    "ClientInfo",
    "Environment",
    "StepNumber",
    "BeatNumber",
    "CycleFloat",
    "BPM",
    "Milliseconds",
    "DestinationConfig",
    "OscDestinationConfig",
    "MidiDestinationConfig",

    # Domain schedule
    "ScheduleEntry",
    "LoopSchedule",
    "SessionCompiler",

    # Domain timeline
    "CuedChange",
    "CuedChangeTimeline",

    # Domain session
    "SessionContainer",
    "SessionValidator",

    # Infrastructure
    "LoopEngine",
    "DestinationRouter",
    "LoopScheduler",
    "OscSender",
    "MidiSender",

    # Application
    "create_loop_engine",
    "app",
]
