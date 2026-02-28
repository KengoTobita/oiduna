"""
Session loader for Loop Engine.

Handles loading destination configurations and session data.
Extracted from LoopEngine to follow Single Responsibility Principle.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from collections.abc import Callable

from ..result import CommandResult

try:
    from oiduna_scheduler.scheduler_models import ScheduledMessageBatch
    from oiduna_scheduler.scheduler import MessageScheduler
    from oiduna_scheduler.router import DestinationRouter
    from oiduna_scheduler.senders import OscDestinationSender, MidiDestinationSender
    from oiduna_models import OscDestinationConfig, MidiDestinationConfig
    from oiduna_models import load_destinations_from_file
except ImportError:
    # Fallback for local development
    from oiduna_scheduler.scheduler_models import ScheduledMessageBatch
    from oiduna_scheduler.scheduler import MessageScheduler
    from oiduna_scheduler.router import DestinationRouter
    from oiduna_scheduler.senders import OscDestinationSender, MidiDestinationSender
    from oiduna_models import OscDestinationConfig, MidiDestinationConfig
    from oiduna_models import load_destinations_from_file

from ..state import RuntimeState

logger = logging.getLogger(__name__)


class SessionLoader:
    """
    Handles session and destination loading for Loop Engine.

    Responsibilities:
    - Load destination configurations from YAML
    - Register destination senders with router
    - Validate and load session data
    - Coordinate with MessageScheduler and RuntimeState

    Extracted from LoopEngine to improve code organization and testability.
    """

    def __init__(
        self,
        destination_router: DestinationRouter,
        message_scheduler: MessageScheduler,
        state: RuntimeState,
        status_update_callback: Callable[[], None],
    ):
        """
        Initialize SessionLoader.

        Args:
            destination_router: Router for message destinations
            message_scheduler: Scheduler for messages
            state: Runtime state manager
            status_update_callback: Callback to trigger status updates
        """
        self._destination_router = destination_router
        self._message_scheduler = message_scheduler
        self._state = state
        self._status_update_callback = status_update_callback
        self._destinations_loaded = False

    @property
    def destinations_loaded(self) -> bool:
        """Check if destinations have been loaded."""
        return self._destinations_loaded

    def load_destinations(self, config_path: Path = Path("destinations.yaml")) -> bool:
        """
        Load destination configurations and register senders.

        Reads destinations.yaml and creates appropriate senders
        (OscDestinationSender, MidiDestinationSender) for each destination.

        If configuration file is not found, logs a warning but continues.
        The new destination-based API will not work without this.

        Args:
            config_path: Path to destinations.yaml file

        Returns:
            True if destinations were loaded successfully, False otherwise
        """
        if not config_path.exists():
            logger.warning(
                f"Destination config file not found: {config_path}. "
                "New destination-based API (/playback/session) will not work. "
                "Using legacy /playback/pattern endpoint is still supported."
            )
            return False

        try:
            # Load and validate destination configurations
            destinations = load_destinations_from_file(config_path)
            logger.info(f"Loaded {len(destinations)} destination(s) from {config_path}")

            # Register each destination with appropriate sender
            for dest_id, dest_config in destinations.items():
                if isinstance(dest_config, OscDestinationConfig):
                    # Create OSC sender
                    sender = OscDestinationSender(
                        host=dest_config.host,
                        port=dest_config.port,
                        address=dest_config.address,
                        use_bundle=dest_config.use_bundle,
                    )
                    self._destination_router.register_destination(dest_id, sender)
                    logger.info(
                        f"Registered OSC destination '{dest_id}': "
                        f"{dest_config.host}:{dest_config.port}{dest_config.address}"
                    )

                elif isinstance(dest_config, MidiDestinationConfig):
                    # Create MIDI sender
                    try:
                        sender = MidiDestinationSender(
                            port_name=dest_config.port_name,
                            default_channel=dest_config.default_channel,
                        )
                        self._destination_router.register_destination(dest_id, sender)
                        logger.info(
                            f"Registered MIDI destination '{dest_id}': "
                            f"{dest_config.port_name} (ch {dest_config.default_channel})"
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed to open MIDI destination '{dest_id}': {e}. "
                            "Skipping this destination."
                        )
                        continue

            self._destinations_loaded = True
            logger.info("Destination routing system initialized")
            return True

        except Exception as e:
            logger.error(f"Failed to load destinations: {e}", exc_info=True)
            logger.warning("Destination-based API will not be available")
            return False

    def load_session(self, payload: dict[str, Any]) -> CommandResult:
        """
        Load session using new destination-based API.

        Accepts ScheduledMessageBatch format with generic messages
        that route to configured destinations.

        Args:
            payload: Dict with keys:
                - messages: List of {destination_id, cycle, step, params}
                - bpm: Tempo (optional, default 120.0)
                - pattern_length: Pattern length in cycles (optional, default 4.0)

        Returns:
            CommandResult indicating success or failure
        """
        # Check if destinations are loaded
        if not self._destinations_loaded:
            return CommandResult.error(
                "Destination configuration not loaded. "
                "Ensure destinations.yaml exists and is valid. "
                "Cannot use session-based API without destination configuration."
            )

        # Parse and validate the batch
        try:
            batch = ScheduledMessageBatch.from_dict(payload)
        except Exception as e:
            return CommandResult.error(f"Invalid session payload: {e}")

        # Validate destinations are registered
        missing_destinations = []
        for dest_id in batch.destinations:
            if not self._destination_router.has_destination(dest_id):
                missing_destinations.append(dest_id)

        if missing_destinations:
            registered = self._destination_router.get_registered_destinations()
            return CommandResult.error(
                f"Session references unregistered destinations: {missing_destinations}. "
                f"Registered destinations: {registered}. "
                f"Check destinations.yaml configuration."
            )

        # Load messages into scheduler
        logger.info(
            f"Loading session: {len(batch.messages)} messages, "
            f"BPM={batch.bpm}, length={batch.pattern_length} cycles"
        )

        self._message_scheduler.load_messages(batch)

        # Update BPM in state
        self._state.set_bpm(batch.bpm)

        # Register track_ids from messages for mute/solo filtering
        for msg in batch.messages:
            track_id = msg.params.get("track_id")
            if track_id:
                self._state.register_track(track_id)

        # Send status update
        self._status_update_callback()

        logger.info(
            f"Session loaded successfully: {self._message_scheduler.message_count} messages "
            f"across {len(self._message_scheduler.occupied_steps)} steps"
        )

        return CommandResult.ok()
