"""
Destination router - sends messages to appropriate destinations.
"""

from __future__ import annotations
from typing import Dict, List, Protocol
from collections import defaultdict

from scheduler_models import ScheduledMessage


class DestinationSender(Protocol):
    """
    Protocol for destination senders.

    Implementations: OscDestinationSender, MidiDestinationSender
    """

    def send_message(self, params: dict) -> None:
        """Send a single message to this destination."""
        ...

    def send_bundle(self, messages: List[dict]) -> None:
        """Send multiple messages as a bundle (for OSC bundles)."""
        ...


class DestinationRouter:
    """
    Routes messages to destinations and sends them.

    Design:
    - Groups messages by destination_id
    - Delegates to appropriate sender (OSC/MIDI)
    - Handles OSC bundles if configured

    Usage:
        >>> router = DestinationRouter()
        >>> router.register_destination("superdirt", osc_sender)
        >>> router.register_destination("volca", midi_sender)
        >>> router.send_messages([msg1, msg2, msg3])
    """

    def __init__(self) -> None:
        """Initialize router with no destinations."""
        self._senders: Dict[str, DestinationSender] = {}

    def register_destination(
        self,
        destination_id: str,
        sender: DestinationSender,
    ) -> None:
        """
        Register a destination sender.

        Args:
            destination_id: Destination identifier (e.g., "superdirt")
            sender: Sender implementation (OscDestinationSender, MidiDestinationSender)
        """
        self._senders[destination_id] = sender

    def unregister_destination(self, destination_id: str) -> None:
        """Remove a destination sender."""
        self._senders.pop(destination_id, None)

    def send_messages(self, messages: List[ScheduledMessage]) -> None:
        """
        Send messages to their destinations.

        Args:
            messages: List of scheduled messages

        Messages are grouped by destination_id and sent together.
        If a destination supports bundles and has multiple messages,
        they're sent as a bundle.
        """
        if not messages:
            return

        # Group messages by destination
        by_destination: Dict[str, List[ScheduledMessage]] = defaultdict(list)
        for msg in messages:
            by_destination[msg.destination_id].append(msg)

        # Send to each destination
        for dest_id, dest_messages in by_destination.items():
            sender = self._senders.get(dest_id)
            if sender is None:
                # Destination not registered - skip silently
                # (Could log warning here)
                continue

            # For now, send individually
            # TODO: Implement bundle support for OSC
            for msg in dest_messages:
                sender.send_message(msg.params)

    def get_registered_destinations(self) -> List[str]:
        """Get list of registered destination IDs."""
        return list(self._senders.keys())
