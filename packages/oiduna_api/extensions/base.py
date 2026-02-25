"""Base extension class for Oiduna API extensions.

Extensions provide session transformation and optional runtime hooks
without polluting the core loop engine.
"""

from abc import ABC, abstractmethod
from typing import Any
from fastapi import APIRouter


class BaseExtension(ABC):
    """
    Base class for all Oiduna extensions.

    Extensions operate in two phases:
    1. Session transformation (API layer, required)
    2. Message finalization (runtime, optional)

    Example:
        >>> class MyExtension(BaseExtension):
        ...     def transform(self, payload: dict) -> dict:
        ...         # Modify session payload
        ...         return payload
        ...
        ...     def before_send_messages(self, messages, current_bpm, current_step):
        ...         # Final adjustments before OSC/MIDI send
        ...         return messages
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize extension with optional configuration.

        Args:
            config: Configuration dict from extensions.yaml or entry_points
        """
        self.config = config or {}

    @abstractmethod
    def transform(self, payload: dict) -> dict:
        """
        Transform session payload at load time (REQUIRED).

        Called once when POST /playback/session is received, after Pydantic
        validation but before passing to loop_engine.

        Args:
            payload: Session dict with keys:
                - messages: list[dict] with destination_id, cycle, step, params
                - bpm: float
                - pattern_length: float

        Returns:
            Transformed payload (same structure)

        Note:
            This is the main extension point. Keep transformations lightweight
            as they run on the HTTP request path.
        """
        ...

    def before_send_messages(
        self,
        messages: list[Any],  # list[ScheduledMessage] but avoid circular import
        current_bpm: float,
        current_step: int,
    ) -> list[Any]:
        """
        Final message adjustments before sending to destinations (OPTIONAL).

        Called at runtime in the step loop, just before DestinationRouter.send_messages().

        Args:
            messages: List of ScheduledMessage instances for this step
            current_bpm: Current BPM (may have changed since session load)
            current_step: Current step position (0-255)

        Returns:
            Modified message list (same length, may have updated params)

        Warning:
            PERFORMANCE CRITICAL - This runs in the timing loop.
            Keep implementation lightweight (<100μs).
            Avoid I/O, logging, or heavy computation.

        Example:
            >>> def before_send_messages(self, messages, current_bpm, current_step):
            ...     # Inject tempo-dependent parameter
            ...     cps = current_bpm / 60.0 / 4.0
            ...     return [
            ...         msg.replace(params={**msg.params, "cps": cps})
            ...         if msg.destination_id == "superdirt"
            ...         else msg
            ...         for msg in messages
            ...     ]
        """
        return messages  # Default: no modification

    def startup(self) -> None:
        """
        Extension startup hook (OPTIONAL).

        Called during FastAPI lifespan startup, before loop_engine starts.
        Use for initialization that doesn't belong in __init__.
        """
        pass

    def shutdown(self) -> None:
        """
        Extension shutdown hook (OPTIONAL).

        Called during FastAPI lifespan shutdown.
        Use for cleanup (close connections, flush logs, etc.).
        """
        pass

    def get_router(self) -> APIRouter | None:
        """
        Provide custom HTTP endpoints (OPTIONAL).

        Returns an APIRouter that will be included in the FastAPI app.

        Returns:
            APIRouter with custom routes, or None

        Example:
            >>> def get_router(self) -> APIRouter:
            ...     router = APIRouter(prefix="/superdirt", tags=["superdirt"])
            ...
            ...     @router.get("/orbits")
            ...     def list_orbits():
            ...         return {"orbits": list(range(12))}
            ...
            ...     return router
        """
        return None
