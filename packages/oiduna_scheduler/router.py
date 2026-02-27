"""
Destination router - sends messages to appropriate destinations.
"""

from __future__ import annotations
from typing import Protocol
from collections import defaultdict
import logging

from oiduna_scheduler.scheduler_models import ScheduledMessage
from oiduna_scheduler.validators import OscValidator, MidiValidator

logger = logging.getLogger(__name__)


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
    - Validates protocol compliance before sending

    Usage:
        >>> router = DestinationRouter()
        >>> router.register_destination("superdirt", osc_sender, protocol="osc")
        >>> router.register_destination("volca", midi_sender, protocol="midi")
        >>> router.send_messages([msg1, msg2, msg3])
    """

    def __init__(
        self,
        osc_validator: Optional[OscValidator] = None,
        midi_validator: Optional[MidiValidator] = None,
    ) -> None:
        """
        Initialize router with no destinations.

        Args:
            osc_validator: OSC protocol validator (default: OscValidator())
            midi_validator: MIDI protocol validator (default: MidiValidator())
        """
        self._senders: Dict[str, DestinationSender] = {}
        self._protocols: Dict[str, str] = {}  # destination_id -> protocol ("osc"/"midi")
        self._osc_validator = osc_validator or OscValidator()
        self._midi_validator = midi_validator or MidiValidator()

    def register_destination(
        self,
        destination_id: str,
        sender: DestinationSender,
        protocol: str = "osc",
    ) -> None:
        """
        Register a destination sender.

        Args:
            destination_id: Destination identifier (e.g., "superdirt")
            sender: Sender implementation (OscDestinationSender, MidiDestinationSender)
            protocol: Protocol type ("osc" or "midi") for validation
        """
        self._senders[destination_id] = sender
        self._protocols[destination_id] = protocol

    def unregister_destination(self, destination_id: str) -> None:
        """Remove a destination sender."""
        self._senders.pop(destination_id, None)
        self._protocols.pop(destination_id, None)

    def send_messages(self, messages: List[ScheduledMessage]) -> None:
        """
        Send messages to their destinations.

        Args:
            messages: List of scheduled messages

        Messages are grouped by destination_id and sent together.
        Protocol validation is performed before sending.
        Invalid messages are logged and skipped.
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
                logger.debug(f"Destination '{dest_id}' not registered, skipping {len(dest_messages)} messages")
                continue

            # Get protocol for this destination
            protocol = self._protocols.get(dest_id, "osc")

            # Validate and send each message
            for msg in dest_messages:
                # Validate protocol compliance
                if protocol == "osc":
                    validation_result = self._osc_validator.validate_message(msg.params)
                elif protocol == "midi":
                    validation_result = self._midi_validator.validate_message(msg.params)
                else:
                    # Unknown protocol - skip validation
                    logger.warning(f"Unknown protocol '{protocol}' for destination '{dest_id}'")
                    validation_result = None

                # Check validation result
                if validation_result and not validation_result.is_valid:
                    # Log validation errors and skip this message
                    logger.warning(
                        f"Invalid {protocol.upper()} message for destination '{dest_id}': "
                        f"{'; '.join(validation_result.errors)}"
                    )
                    continue

                # Send valid message
                sender.send_message(msg.params)

    def get_registered_destinations(self) -> List[str]:
        """Get list of registered destination IDs."""
        return list(self._senders.keys())
