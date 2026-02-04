"""
Session IR Protocol for Three-Layer IR Architecture.

This protocol defines the framework's entry point interface (Layer 1).
DSL compilers produce objects conforming to this protocol, which can then
be consumed by the runtime (Layer 2) via IPC.

Design:
- SessionIRProtocol: Interface for compiled session data
- Supports serialization for IPC (to_dict/from_dict)

Usage:
    # DSL compiler produces Session IR
    compiled = dsl_compiler.compile(source_code)
    assert isinstance(compiled, SessionIRProtocol)

    # Send via IPC
    data = compiled.to_dict()
    ipc.send(data)

    # Runtime receives and reconstructs
    received = CompiledSession.from_dict(data)
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class SessionIRProtocol(Protocol):
    """
    Protocol for Session IR (Layer 1) objects.

    This is the framework's standard interface for compiled session data.
    DSL frontends produce objects conforming to this protocol, which are
    then consumed by the runtime backend.

    The protocol ensures:
    - Serialization capability for IPC (to_dict)
    - Reconstruction from serialized data (from_dict)
    - Access to session metadata

    Implementations:
        - CompiledSession (mars_common.models.compiled_session)

    Example:
        >>> class MyCompiledSession:
        ...     def to_dict(self) -> dict[str, Any]:
        ...         return {"bpm": self.bpm, "tracks": {...}}
        ...
        ...     @classmethod
        ...     def from_dict(cls, data: dict[str, Any]) -> "MyCompiledSession":
        ...         return cls(bpm=data["bpm"], ...)
    """

    @property
    def bpm(self) -> float:
        """Session tempo in beats per minute."""
        ...

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize session to dictionary for IPC transmission.

        The returned dict should be JSON-serializable and contain
        all information needed to reconstruct the session.

        Returns:
            Dictionary representation of the session
        """
        ...

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionIRProtocol:
        """
        Reconstruct session from dictionary.

        Args:
            data: Dictionary from to_dict() or IPC

        Returns:
            Reconstructed session object
        """
        ...


@runtime_checkable
class SequenceProtocol(Protocol):
    """
    Protocol for sequence data within Session IR.

    Sequences contain the event data (patterns) for a track.

    Implementations:
        - Sequence (mars_common.models.sequence)
    """

    @property
    def length(self) -> int:
        """Sequence length in steps."""
        ...

    def get_events_at(self, step: int) -> list[Any]:
        """
        Get all events at a specific step.

        Args:
            step: Step index (0-based)

        Returns:
            List of events at this step (empty if none)
        """
        ...

    def to_dict(self) -> dict[str, Any]:
        """Serialize sequence to dictionary."""
        ...


@runtime_checkable
class TrackProtocol(Protocol):
    """
    Protocol for track definitions within Session IR.

    Tracks contain sound parameters, effects, and modulations.

    Implementations:
        - Track (mars_common.models.track)
    """

    @property
    def muted(self) -> bool:
        """Whether track is muted."""
        ...

    @property
    def solo(self) -> bool:
        """Whether track is soloed."""
        ...

    def to_dict(self) -> dict[str, Any]:
        """Serialize track to dictionary."""
        ...
