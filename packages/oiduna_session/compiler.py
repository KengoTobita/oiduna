"""
SessionCompiler - compile Session to ScheduledMessageBatch.

Extracts active patterns, merges parameters, and generates
the message batch for the Loop Engine.
"""

from oiduna_models import Session
from oiduna_scheduler.scheduler_models import ScheduledMessage, ScheduledMessageBatch


class SessionCompiler:
    """
    Compile Session state to ScheduledMessageBatch for Loop Engine.

    The compiler:
    1. Iterates through all tracks
    2. For each track, finds active patterns
    3. For each event in active patterns:
       - Merges Track.base_params with Event.params
       - Adds track_id for mute/solo filtering
       - Creates ScheduledMessage
    4. Returns ScheduledMessageBatch with all messages

    Example:
        >>> from oiduna_models import Session
        >>> session = Session()
        >>> # ... populate session with tracks/patterns ...
        >>> batch = SessionCompiler.compile(session)
        >>> len(batch.messages)
        42
    """

    @staticmethod
    def compile(session: Session) -> ScheduledMessageBatch:
        """
        Compile Session to ScheduledMessageBatch.

        Args:
            session: Session state to compile

        Returns:
            ScheduledMessageBatch ready for Loop Engine

        Example:
            >>> batch = SessionCompiler.compile(session)
            >>> batch.bpm
            120.0
            >>> len(batch.messages)
            10
        """
        messages = []

        for track in session.tracks.values():
            for pattern in track.patterns.values():
                # Skip inactive patterns
                if not pattern.active:
                    continue

                # Generate messages for each event
                for event in pattern.events:
                    # Merge base_params with event params (event params override)
                    params = {**track.base_params, **event.params}

                    # Add track_id for mute/solo filtering
                    params["track_id"] = track.track_id

                    # Create scheduled message
                    msg = ScheduledMessage(
                        destination_id=track.destination_id,
                        cycle=event.cycle,
                        step=event.step,
                        params=params,
                    )
                    messages.append(msg)

        return ScheduledMessageBatch(
            messages=tuple(messages),
            bpm=session.environment.bpm,
            pattern_length=4.0,  # Fixed (not used by 256-step engine)
        )

    @staticmethod
    def compile_track(session: Session, track_id: str) -> list[ScheduledMessage]:
        """
        Compile a single track (for partial updates).

        Args:
            session: Session state
            track_id: Track to compile

        Returns:
            List of ScheduledMessages for this track

        Raises:
            KeyError: If track_id not found
        """
        track = session.tracks[track_id]
        messages = []

        for pattern in track.patterns.values():
            if not pattern.active:
                continue

            for event in pattern.events:
                params = {**track.base_params, **event.params}
                params["track_id"] = track.track_id

                msg = ScheduledMessage(
                    destination_id=track.destination_id,
                    cycle=event.cycle,
                    step=event.step,
                    params=params,
                )
                messages.append(msg)

        return messages
