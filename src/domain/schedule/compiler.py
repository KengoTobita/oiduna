"""
SessionCompiler - compile Session to LoopSchedule.

Extracts active patterns, merges parameters, and generates
the message batch for the Loop Engine.
"""

from typing import TYPE_CHECKING

from oiduna.domain.models import Session
from oiduna.domain.schedule.models import ScheduleEntry, LoopSchedule

if TYPE_CHECKING:
    from oiduna.domain.models import Track, PatternEvent


class SessionCompiler:
    """
    Compile Session state to LoopSchedule for Loop Engine.

    The compiler:
    1. Iterates through all tracks
    2. For each track, finds active patterns
    3. For each event in active patterns:
       - Merges Track.base_params with Event.params
       - Adds track_id for mute/solo filtering
       - Creates ScheduleEntry
    4. Returns LoopSchedule with all messages

    Example:
        >>> from oiduna_models import Session
        >>> session = Session()
        >>> # ... populate session with tracks/patterns ...
        >>> batch = SessionCompiler.compile(session)
        >>> len(batch.messages)
        42
    """

    @staticmethod
    def _create_message_from_event(
        track: "Track", event: "PatternEvent"
    ) -> ScheduleEntry:
        """
        Create a ScheduleEntry from a Track and Event.

        Merges Track.base_params with Event.params (event params override),
        adds track_id for mute/solo filtering.

        Args:
            track: Track containing the event
            event: Event to convert to message

        Returns:
            ScheduleEntry ready for Loop Engine
        """
        # Merge base_params with event params (event params override)
        params = {**track.base_params, **event.params}

        # Add track_id for mute/solo filtering
        params["track_id"] = track.track_id

        # Create scheduled message
        return ScheduleEntry(
            destination_id=track.destination_id,
            cycle=event.cycle,
            step=event.step,
            params=params,
        )

    @staticmethod
    def compile(session: Session) -> LoopSchedule:
        """
        Compile Session to LoopSchedule.

        Args:
            session: Session state to compile

        Returns:
            LoopSchedule ready for Loop Engine

        Raises:
            ValueError: If any track references non-existent destination

        Example:
            >>> batch = SessionCompiler.compile(session)
            >>> batch.bpm
            120.0
            >>> len(batch.messages)
            10
        """
        messages = []
        invalid_destinations: list[dict[str, str]] = []

        for track in session.tracks.values():
            # Validate destination exists
            if track.destination_id not in session.destinations:
                invalid_destinations.append({
                    "track_id": track.track_id,
                    "destination_id": track.destination_id
                })

            for pattern in track.patterns.values():
                # Skip inactive or archived patterns
                if not pattern.active or pattern.archived:
                    continue

                # Generate messages for each event
                for event in pattern.events:
                    msg = SessionCompiler._create_message_from_event(track, event)
                    messages.append(msg)

        # Fail fast if invalid destinations found
        if invalid_destinations:
            available = list(session.destinations.keys())
            error_details = ", ".join(
                f"{item['track_id']}\u2192{item['destination_id']}"
                for item in invalid_destinations
            )
            raise ValueError(
                f"Session contains tracks with non-existent destinations: {error_details}. "
                f"Available destinations: {available}"
            )

        return LoopSchedule(
            entries=tuple(messages),
            bpm=session.environment.bpm,
            pattern_length=4.0,  # Fixed (not used by 256-step engine)
            # destinations auto-inferred from entries (property)
        )

    @staticmethod
    def compile_track(session: Session, track_id: str) -> list[ScheduleEntry]:
        """
        Compile a single track (for partial updates).

        Args:
            session: Session state
            track_id: Track to compile

        Returns:
            List of ScheduleEntrys for this track

        Raises:
            KeyError: If track_id not found
        """
        track = session.tracks[track_id]
        messages = []

        for pattern in track.patterns.values():
            # Skip inactive or archived patterns
            if not pattern.active or pattern.archived:
                continue

            for event in pattern.events:
                msg = SessionCompiler._create_message_from_event(track, event)
                messages.append(msg)

        return messages
