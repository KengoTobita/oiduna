"""
Oiduna Loop Engine

Main loop engine that orchestrates:
- Step sequencer (16th notes)
- MIDI clock (24 PPQ)
- OSC output to SuperDirt
- MIDI output
- In-process IPC with oiduna_api

Refactored using Martin Fowler patterns:
- Extract Class: StepProcessor, NoteScheduler, ClockGenerator
- Single Responsibility Principle
- Dependency Injection: Protocol-based DI for testability
"""

from __future__ import annotations

import asyncio
import logging
import time
import traceback
from typing import Any

from pydantic import ValidationError

from ..commands import (
    BpmCommand,
    CompileCommand,
    MidiPanicCommand,
    MidiPortCommand,
    MuteCommand,
    PanicCommand,
    PauseCommand,
    PlayCommand,
    SceneCommand,
    ScenesCommand,
    SoloCommand,
    StopCommand,
)
from ..protocols import CommandSource, MidiOutput, OscOutput, StateSink
from ..result import CommandResult
from ..state import PlaybackState, RuntimeState
from .clock_generator import ClockGenerator
from .note_scheduler import NoteScheduler
from .step_processor import StepProcessor

# New destination-based architecture imports
from pathlib import Path

try:
    from oiduna_scheduler.scheduler_models import ScheduledMessageBatch
    from oiduna_scheduler.scheduler import MessageScheduler
    from oiduna_scheduler.router import DestinationRouter
    from oiduna_scheduler.senders import OscDestinationSender, MidiDestinationSender
    from oiduna_destination.destination_models import OscDestinationConfig, MidiDestinationConfig
    from oiduna_destination.loader import load_destinations_from_file
except ImportError:
    # Fallback for local development
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "oiduna_scheduler"))
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "oiduna_destination"))
    from scheduler_models import ScheduledMessageBatch
    from scheduler import MessageScheduler
    from router import DestinationRouter
    from senders import OscDestinationSender, MidiDestinationSender
    from destination_models import OscDestinationConfig, MidiDestinationConfig
    from loader import load_destinations_from_file

logger = logging.getLogger(__name__)


class LoopEngine:
    """
    Main loop engine for Oiduna.

    Orchestrates step processing, MIDI clock, and IPC.
    Delegates detailed processing to specialized components.

    Dependencies are injected via constructor for testability.
    Use create_loop_engine() factory for production instances.
    """

    # Heartbeat configuration (Phase 4: Health monitoring)
    HEARTBEAT_INTERVAL: float = 5.0  # seconds

    # Drift reset configuration (inspired by Tidal's clockSkipTicks)
    # If clock drifts more than this threshold, reset anchor instead of catching up
    DRIFT_RESET_THRESHOLD_MS: float = 50.0  # Reset if drift exceeds 50ms
    DRIFT_WARNING_THRESHOLD_MS: float = 20.0  # Log warning if drift exceeds 20ms

    # Command loop backoff configuration (CPU optimization)
    # Uses exponential backoff to reduce CPU usage when idle
    # Inspired by TidalCycles' clockFrameTimespan (50ms = 20 FPS)
    COMMAND_POLL_MIN_INTERVAL: float = 0.001  # 1ms minimum (responsive)
    COMMAND_POLL_MAX_INTERVAL: float = 0.050  # 50ms maximum (TidalCycles-inspired)

    def __init__(
        self,
        osc: OscOutput,
        midi: MidiOutput,
        commands: CommandSource,
        publisher: StateSink,
        before_send_hooks: list | None = None,
    ):
        """
        Initialize LoopEngine with injected dependencies.

        Args:
            osc: OSC output (OscSender or mock)
            midi: MIDI output (MidiSender or mock)
            commands: Command source (CommandReceiver or mock)
            publisher: State sink (StatePublisher or mock)
            before_send_hooks: Optional hooks for message transformation before sending.
                Each hook is called with (messages, current_bpm, current_step) -> messages.
                Provided by extension system for runtime transformations (e.g., cps injection).
        """
        # State (v5: RuntimeState with CompiledSession)
        self.state = RuntimeState()

        # Output (injected)
        self._osc = osc
        self._midi = midi

        # IPC (injected)
        self._commands = commands
        self._publisher = publisher

        # Processors (Martin Fowler: Extract Class)
        self._step_processor = StepProcessor(self._osc)
        self._note_scheduler = NoteScheduler(self._midi)
        self._clock_generator = ClockGenerator(self._midi)

        # Control flags
        self._running = False
        self._midi_enabled = False

        # Drift correction state (Phase 1: Timing improvement)
        self._step_anchor_time: float | None = None
        self._step_count: int = 0

        # BPM change grace: suppress next drift reset notification
        # after BPM change to avoid false positives from timing transitions
        self._suppress_next_drift_reset: bool = False

        # Drift reset statistics (for monitoring and debugging)
        self._drift_stats: dict[str, float | int] = {
            "reset_count": 0,
            "max_drift_ms": 0.0,
            "total_skipped_steps": 0,
            "last_reset_drift_ms": 0.0,
        }

        # Connection status tracking (Phase 3: Error notification)
        self._connection_status: dict[str, bool] = {
            "midi": False,
            "osc": False,
        }

        # New destination-based architecture (Milestone 3)
        self._message_scheduler = MessageScheduler()
        self._destination_router = DestinationRouter()
        self._destinations_loaded = False

        # Extension hooks (API layer integration)
        self._before_send_hooks = before_send_hooks or []

    # ================================================================
    # Lifecycle
    # ================================================================

    def start(self) -> None:
        """Start the loop engine"""
        # Connect outputs
        self._osc.connect()
        if self._midi.connect():
            self._midi_enabled = True
            logger.info("MIDI enabled")
        else:
            logger.info("MIDI disabled (no ports available)")

        # Connect IPC
        self._commands.connect()
        self._publisher.connect()

        # Register command handlers
        self._register_handlers()

        # Load destination configurations (new architecture)
        self._load_destinations()

        logger.info("Loop engine started")

    def stop(self) -> None:
        """Stop the loop engine"""
        self._running = False

        # Stop playback if not already stopped
        if self.state.playback_state != PlaybackState.STOPPED:
            self._handle_stop({})

        # Disconnect
        self._osc.disconnect()
        self._midi.disconnect()
        self._commands.disconnect()
        self._publisher.disconnect()

        logger.info("Loop engine stopped")

    def _register_handlers(self) -> None:
        """Register command handlers"""
        self._commands.register_handler("compile", self._handle_compile)
        self._commands.register_handler("session", self._handle_session)  # New destination-based API
        self._commands.register_handler("play", self._handle_play)
        self._commands.register_handler("stop", self._handle_stop)
        self._commands.register_handler("pause", self._handle_pause)
        self._commands.register_handler("mute", self._handle_mute)
        self._commands.register_handler("solo", self._handle_solo)
        self._commands.register_handler("bpm", self._handle_bpm)
        self._commands.register_handler("midi_port", self._handle_midi_port)
        self._commands.register_handler("midi_panic", self._handle_midi_panic)
        self._commands.register_handler("panic", self._handle_panic)
        self._commands.register_handler("scene", self._handle_scene)
        self._commands.register_handler("scenes", self._handle_scenes)

    def _load_destinations(self) -> None:
        """
        Load destination configurations and register senders.

        Reads destinations.yaml and creates appropriate senders
        (OscDestinationSender, MidiDestinationSender) for each destination.

        If configuration file is not found, logs a warning but continues.
        The new destination-based API will not work without this.
        """
        config_path = Path("destinations.yaml")

        if not config_path.exists():
            logger.warning(
                f"Destination config file not found: {config_path}. "
                "New destination-based API (/playback/session) will not work. "
                "Using legacy /playback/pattern endpoint is still supported."
            )
            return

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

        except Exception as e:
            logger.error(f"Failed to load destinations: {e}", exc_info=True)
            logger.warning("Destination-based API will not be available")

    # ================================================================
    # Command Handlers
    # ================================================================

    def _handle_compile(self, payload: dict[str, Any]) -> CommandResult:
        """
        Load compiled session data with apply timing support.

        If not playing or apply timing is "now", applies immediately.
        Otherwise queues changes to be applied at the specified timing.

        When track_ids are specified in apply, only those tracks will have
        events; other tracks will have their events cleared (exclusive apply).
        """
        try:
            # Validate payload with Pydantic
            cmd = CompileCommand(**payload)
        except ValidationError as e:
            return CommandResult.error(f"Invalid compile command: {e}")

        # Extract apply info from payload
        apply_data = payload.get("apply")

        # Determine timing and track_ids
        if apply_data:
            timing = apply_data.get("timing", "bar")
            track_ids = apply_data.get("track_ids", [])
        else:
            # Default: apply all at bar boundary
            timing = "bar"
            track_ids = []

        # If not playing or timing is "now", apply immediately
        if not self.state.playing or timing == "now":
            logger.info("Loading compiled session (immediate)")
            # Always load the full session first (environment, tracks, sequences)
            self.state.load_compiled_session(payload)

            # If specific tracks were specified in apply, clear events for
            # non-specified tracks (exclusive apply behavior)
            if track_ids:
                self.state.clear_non_specified_track_events(track_ids)

            # Send status update (includes BPM) and track info for Monitor display
            self._schedule_status_update()
            self._schedule_tracks_update()
        else:
            # Queue for later application
            logger.info(f"Queuing session change (apply @{timing})")
            self.state.set_pending_change(
                session_data=payload,
                timing=timing,
                track_ids=track_ids,
            )

        return CommandResult.ok()

    def _handle_session(self, payload: dict[str, Any]) -> CommandResult:
        """
        Load session using new destination-based API (Milestone 3).

        Accepts ScheduledMessageBatch format with generic messages
        that route to configured destinations.

        Args:
            payload: Dict with keys:
                - messages: List of {destination_id, cycle, step, params}
                - bpm: Tempo (optional, default 120.0)
                - pattern_length: Pattern length in cycles (optional, default 4.0)
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

        # Load messages into scheduler
        logger.info(
            f"Loading session: {len(batch.messages)} messages, "
            f"BPM={batch.bpm}, length={batch.pattern_length} cycles"
        )

        self._message_scheduler.load_messages(batch)

        # Update BPM in state (for compatibility with existing code)
        self.state.bpm = batch.bpm

        # Send status update
        self._schedule_status_update()

        logger.info(
            f"Session loaded successfully: {self._message_scheduler.message_count} messages "
            f"across {len(self._message_scheduler.occupied_steps)} steps"
        )

        return CommandResult.ok()

    def _handle_play(self, payload: dict[str, Any]) -> CommandResult:
        """Start or resume playback (like video player play button)"""
        try:
            # Validate payload with Pydantic
            cmd = PlayCommand(**payload)
        except ValidationError as e:
            return CommandResult.error(f"Invalid play command: {e}")

        current_state = self.state.playback_state

        if current_state == PlaybackState.PLAYING:
            # Already playing, do nothing
            return CommandResult.ok("Already playing")

        if current_state == PlaybackState.STOPPED:
            # Starting from stopped state - position already at 0
            self.state.playback_state = PlaybackState.PLAYING
            if self._midi_enabled:
                self._clock_generator.send_start()
            logger.info("Playback started from beginning")

        elif current_state == PlaybackState.PAUSED:
            # Resuming from paused state - keep current position
            self.state.playback_state = PlaybackState.PLAYING
            if self._midi_enabled:
                self._clock_generator.send_continue()
            logger.info(f"Playback resumed from step {self.state.position.step}")

        # Send status and tracks update (non-blocking)
        self._schedule_status_update()
        self._schedule_tracks_update()

        return CommandResult.ok()

    def _handle_stop(self, payload: dict[str, Any]) -> CommandResult:
        """Stop playback and reset to beginning (like video player stop button)"""
        try:
            # Validate payload with Pydantic
            cmd = StopCommand(**payload)
        except ValidationError as e:
            return CommandResult.error(f"Invalid stop command: {e}")

        if self.state.playback_state == PlaybackState.STOPPED:
            # Already stopped, do nothing
            return CommandResult.ok("Already stopped")

        # Clear note scheduler
        self._note_scheduler.clear_all()

        # Send MIDI stop if was playing
        if self.state.playback_state == PlaybackState.PLAYING and self._midi_enabled:
            self._clock_generator.send_stop()

        # Reset position and set state
        self.state.reset_position()
        self.state.playback_state = PlaybackState.STOPPED

        # Reset drift correction anchor (Phase 1)
        self._step_anchor_time = None
        self._step_count = 0

        logger.info("Playback stopped, position reset")

        # Send status update (non-blocking)
        self._schedule_status_update()

        return CommandResult.ok()

    def _handle_pause(self, payload: dict[str, Any]) -> CommandResult:
        """Pause playback, maintaining position (like video player pause button)"""
        try:
            # Validate payload with Pydantic
            cmd = PauseCommand(**payload)
        except ValidationError as e:
            return CommandResult.error(f"Invalid pause command: {e}")

        if self.state.playback_state != PlaybackState.PLAYING:
            # Not playing, do nothing
            return CommandResult.ok("Not playing")

        # Clear note scheduler
        self._note_scheduler.clear_all()

        # Send MIDI stop (enables proper resume with CONTINUE)
        if self._midi_enabled:
            self._clock_generator.send_stop()

        # Set paused state (position is maintained)
        self.state.playback_state = PlaybackState.PAUSED

        # Reset drift correction anchor (Phase 1)
        # Will re-anchor when playback resumes
        self._step_anchor_time = None

        logger.info(f"Playback paused at step {self.state.position.step}")

        # Send status update (non-blocking)
        self._schedule_status_update()

        return CommandResult.ok()

    def _handle_mute(self, payload: dict[str, Any]) -> CommandResult:
        """Mute/unmute a track"""
        try:
            # Validate payload with Pydantic
            cmd = MuteCommand(**payload)
        except ValidationError as e:
            return CommandResult.error(f"Invalid mute command: {e}")

        if self.state.set_track_mute(cmd.track_id, cmd.mute):
            logger.debug(f"Track '{cmd.track_id}' mute={cmd.mute}")
            return CommandResult.ok()
        else:
            return CommandResult.error(f"Track '{cmd.track_id}' not found")

    def _handle_solo(self, payload: dict[str, Any]) -> CommandResult:
        """Solo/unsolo a track"""
        try:
            # Validate payload with Pydantic
            cmd = SoloCommand(**payload)
        except ValidationError as e:
            return CommandResult.error(f"Invalid solo command: {e}")

        if self.state.set_track_solo(cmd.track_id, cmd.solo):
            logger.debug(f"Track '{cmd.track_id}' solo={cmd.solo}")
            return CommandResult.ok()
        else:
            return CommandResult.error(f"Track '{cmd.track_id}' not found")

    def _handle_bpm(self, payload: dict[str, Any]) -> CommandResult:
        """
        Change BPM with proper anchor reset for smooth transitions.

        When BPM changes during playback, we must reset the timing anchor
        to prevent false drift detection. The step_duration changes but
        the anchor was set based on the old duration, which would cause
        large apparent drift.

        Both LoopEngine (step sequencer) and ClockGenerator (MIDI clock)
        anchors are reset to ensure synchronized smooth transitions.

        A grace period is set to suppress drift reset notifications during
        the transition, as the previous sleep may still be in progress.
        """
        try:
            # Validate payload with Pydantic
            cmd = BpmCommand(**payload)
        except ValidationError as e:
            return CommandResult.error(f"Invalid bpm command: {e}")

        old_bpm = self.state.bpm
        self.state.set_bpm(cmd.bpm)

        # Reset anchors during playback to prevent false drift detection
        if self.state.playing and self._step_anchor_time is not None:
            current_time = time.perf_counter()
            self._step_anchor_time = current_time
            self._step_count = 0

            # Suppress the next drift reset notification (flag-based, not time-based)
            # This avoids race conditions with async timing
            self._suppress_next_drift_reset = True

            # Also reset MIDI clock anchor with suppression
            self._clock_generator.suppress_next_drift_reset()

            logger.debug(
                f"BPM changed {old_bpm} → {cmd.bpm}, anchors reset (drift suppression enabled)"
            )
        else:
            logger.debug(f"BPM changed to {cmd.bpm}")

        return CommandResult.ok()

    def _handle_midi_port(self, payload: dict[str, Any]) -> CommandResult:
        """Change MIDI output port"""
        try:
            # Validate payload with Pydantic
            cmd = MidiPortCommand(**payload)
        except ValidationError as e:
            return CommandResult.error(f"Invalid midi_port command: {e}")

        if self._midi.set_port(cmd.port_name):
            self._midi_enabled = True
            logger.info(f"MIDI port changed to: {cmd.port_name}")
            return CommandResult.ok()
        else:
            self._midi_enabled = False
            logger.warning(f"Failed to connect to MIDI port: {cmd.port_name}")
            return CommandResult.error(f"Failed to connect to MIDI port: {cmd.port_name}")

    def _silence_all_notes(self) -> None:
        """
        Turn off all MIDI notes and clear scheduled note-offs.

        Extracted common logic for panic handlers (Martin Fowler: Extract Method).
        """
        if self._midi_enabled:
            self._midi.all_notes_off()
        self._note_scheduler.clear_all()

    def _handle_midi_panic(self, payload: dict[str, Any]) -> CommandResult:
        """
        MIDI-only panic: turn off all MIDI notes without stopping playback.

        Use for: Notes stuck while playback should continue.
        """
        try:
            # Validate payload with Pydantic
            cmd = MidiPanicCommand(**payload)
        except ValidationError as e:
            return CommandResult.error(f"Invalid midi_panic command: {e}")

        self._silence_all_notes()
        logger.warning("MIDI PANIC: All notes off (playback continues)")
        return CommandResult.ok()

    def _handle_panic(self, payload: dict[str, Any]) -> CommandResult:
        """
        Full emergency stop: turn off all notes and stop playback.

        Use for: Complete emergency stop of all audio output.
        """
        try:
            # Validate payload with Pydantic
            cmd = PanicCommand(**payload)
        except ValidationError as e:
            return CommandResult.error(f"Invalid panic command: {e}")

        self._silence_all_notes()

        # Stop playback and reset position
        self.state.reset_position()
        self.state.playback_state = PlaybackState.STOPPED

        # Reset drift correction anchor
        self._step_anchor_time = None
        self._step_count = 0

        logger.warning("PANIC: Emergency stop executed")
        self._schedule_status_update()

        return CommandResult.ok()

    def _handle_scene(self, payload: dict[str, Any]) -> CommandResult:
        """
        Activate a scene by name.

        Payload:
            name: Scene name to activate
        """
        try:
            # Validate payload with Pydantic
            cmd = SceneCommand(**payload)
        except ValidationError as e:
            return CommandResult.error(f"Invalid scene command: {e}")

        if self.state.activate_scene(cmd.name):
            logger.info(f"Scene activated: {cmd.name}")
            self._schedule_status_update()
            self._schedule_tracks_update()
            return CommandResult.ok()
        else:
            logger.warning(f"Scene not found: {cmd.name}")
            return CommandResult.error(f"Scene not found: {cmd.name}")

    def _handle_scenes(self, payload: dict[str, Any]) -> CommandResult:
        """
        Request scene list update.

        Scene information is delivered via SSE status updates.
        This handler triggers a status update to broadcast current scenes.
        """
        try:
            # Validate payload with Pydantic
            cmd = ScenesCommand(**payload)
        except ValidationError as e:
            return CommandResult.error(f"Invalid scenes command: {e}")

        # Trigger status update to broadcast scene information via SSE
        self._schedule_status_update()

        return CommandResult.ok()

    # ================================================================
    # Public API Methods
    # ================================================================

    def compile(self, session_data: dict[str, Any]) -> CommandResult:
        """
        Public API: Load compiled session data.

        Args:
            session_data: CompiledSession dictionary with environment, tracks, sequences

        Returns:
            CommandResult indicating success or failure
        """
        return self._handle_compile(session_data)

    def play(self) -> CommandResult:
        """
        Public API: Start or resume playback.

        Returns:
            CommandResult indicating success or failure
        """
        return self._handle_play({})

    def stop_playback(self) -> CommandResult:
        """
        Public API: Stop playback and reset position.

        Returns:
            CommandResult indicating success or failure
        """
        return self._handle_stop({})

    def pause(self) -> CommandResult:
        """
        Public API: Pause playback at current position.

        Returns:
            CommandResult indicating success or failure
        """
        return self._handle_pause({})

    def mute_track(self, track_id: str, mute: bool = True) -> CommandResult:
        """
        Public API: Mute or unmute a track.

        Args:
            track_id: Track identifier
            mute: True to mute, False to unmute

        Returns:
            CommandResult indicating success or failure
        """
        return self._handle_mute({"track_id": track_id, "mute": mute})

    def solo_track(self, track_id: str, solo: bool = True) -> CommandResult:
        """
        Public API: Solo or unsolo a track.

        Args:
            track_id: Track identifier
            solo: True to solo, False to unsolo

        Returns:
            CommandResult indicating success or failure
        """
        return self._handle_solo({"track_id": track_id, "solo": solo})

    def set_bpm(self, bpm: float) -> CommandResult:
        """
        Public API: Change the BPM.

        Args:
            bpm: Beats per minute (must be positive)

        Returns:
            CommandResult indicating success or failure
        """
        return self._handle_bpm({"bpm": bpm})

    def select_midi_port(self, port_name: str) -> CommandResult:
        """
        Public API: Select MIDI output port.

        Args:
            port_name: Name of the MIDI port to connect to

        Returns:
            CommandResult indicating success or failure
        """
        return self._handle_midi_port({"port_name": port_name})

    def midi_panic(self) -> CommandResult:
        """
        Public API: Send MIDI panic (all notes off) without stopping playback.

        Returns:
            CommandResult indicating success or failure
        """
        return self._handle_midi_panic({})

    def activate_scene(self, scene_name: str) -> CommandResult:
        """
        Public API: Activate a scene by name.

        Args:
            scene_name: Name of the scene to activate

        Returns:
            CommandResult indicating success or failure
        """
        return self._handle_scene({"name": scene_name})

    async def _check_connections(self) -> None:
        """
        Check connection status and notify on changes.

        Phase 3: This method checks MIDI and OSC connection status
        and sends error notifications when connections are lost.
        """
        current_status = {
            "midi": self._midi.is_connected,
            "osc": self._osc.is_connected,
        }

        # Check for status changes and notify
        for key, connected in current_status.items():
            if self._connection_status[key] and not connected:
                # Was connected, now disconnected -> send error
                error_code = f"CONNECTION_LOST_{key.upper()}"
                await self._publisher.send_error(
                    error_code,
                    f"{key.upper()} connection lost"
                )
                logger.warning(f"{key.upper()} connection lost")

        # Update stored status
        self._connection_status.update(current_status)

    async def send_heartbeat(self) -> None:
        """
        Send heartbeat message to API.

        Phase 4: This allows the API to detect if the loop engine is still alive.
        """
        await self._publisher.send("heartbeat", {
            "timestamp": time.perf_counter(),
        })

    async def _heartbeat_loop(self) -> None:
        """
        Periodically send heartbeat messages and check connections.

        Phase 3: Check connection status and notify on changes.
        Phase 4: Send heartbeat for health monitoring.
        """
        while self._running:
            await self._check_connections()
            await self.send_heartbeat()
            await asyncio.sleep(self.HEARTBEAT_INTERVAL)

    # ================================================================
    # Main Loop
    # ================================================================

    async def run(self) -> None:
        """Run the main loop"""
        self._running = True

        await asyncio.gather(
            self._command_loop(),
            self._step_loop(),
            self._clock_loop(),
            self._note_off_loop(),
            self._heartbeat_loop(),
        )

    async def _command_loop(self) -> None:
        """
        Process incoming commands with exponential backoff.

        Uses adaptive sleep to reduce CPU usage when idle:
        - Starts at COMMAND_POLL_MIN_INTERVAL sleep
        - Doubles on each idle iteration (no commands)
        - Caps at COMMAND_POLL_MAX_INTERVAL for panic responsiveness
        - Resets to minimum when commands are received
        """
        backoff = self.COMMAND_POLL_MIN_INTERVAL

        while self._running:
            try:
                processed = await self._commands.process_commands()
                if processed > 0:
                    backoff = self.COMMAND_POLL_MIN_INTERVAL
                else:
                    backoff = min(self.COMMAND_POLL_MAX_INTERVAL, backoff * 2)
            except Exception as e:
                logger.error(f"Command processing error: {e}\n{traceback.format_exc()}")
            await asyncio.sleep(backoff)

    async def _step_loop(self) -> None:
        """
        16th note step loop with drift correction and auto-reset.

        Delegates event processing to StepProcessor.
        Applies pending changes at appropriate timing boundaries.

        Drift correction (Phase 1):
        - Uses anchor time to calculate expected step times
        - Compensates for accumulated drift over many steps

        Drift reset (inspired by Tidal's clockSkipTicks):
        - If drift exceeds threshold, reset anchor instead of catching up
        - Prevents burst playback after CPU spikes or sleep/wake
        """
        while self._running:
            if not self.state.playing:
                # Reset anchor when not playing
                self._step_anchor_time = None
                self._step_count = 0
                await asyncio.sleep(0.001)
                continue

            # Initialize anchor time when playback starts
            if self._step_anchor_time is None:
                self._step_anchor_time = time.perf_counter()
                self._step_count = 0

            current_time = time.perf_counter()
            step_duration = self.state.step_duration

            # === Drift detection ===
            expected_time = self._step_anchor_time + (self._step_count * step_duration)
            drift_seconds = current_time - expected_time
            drift_ms = drift_seconds * 1000

            # Update max drift statistic
            if abs(drift_ms) > self._drift_stats["max_drift_ms"]:
                self._drift_stats["max_drift_ms"] = abs(drift_ms)

            # === Drift reset logic (inspired by Tidal) ===
            if abs(drift_ms) > self.DRIFT_RESET_THRESHOLD_MS:
                if self._suppress_next_drift_reset:
                    # Suppress notification after BPM change (expected drift)
                    self._step_anchor_time = current_time
                    self._step_count = 0
                    self._suppress_next_drift_reset = False
                    logger.debug(
                        f"Drift {drift_ms:.1f}ms suppressed (BPM change transition)"
                    )
                else:
                    # Normal case: report drift reset to user
                    await self._handle_drift_reset(drift_ms, current_time)

                # After reset, we're about to sleep for one step_duration.
                # Set step_count to 1 so next iteration expects: anchor + 1 * step_duration
                # This prevents infinite reset loop where drift = sleep_time each iteration.
                self._step_count = 1

                # Wait one step duration before next iteration
                await asyncio.sleep(step_duration)
                continue
            elif abs(drift_ms) > self.DRIFT_WARNING_THRESHOLD_MS:
                # Warning level drift - log but continue with normal correction
                logger.debug(f"Clock drift warning: {drift_ms:.1f}ms")

            try:
                # Check and apply pending changes at timing boundaries
                if self.state.should_apply_pending():
                    logger.info(f"Applying pending changes at step {self.state.position.step}")

                    # Track BPM before apply to detect changes
                    old_bpm = self.state.bpm

                    self.state.apply_pending_changes()

                    # If BPM changed during apply, reset anchors and suppress drift
                    if self.state.bpm != old_bpm:
                        current_time = time.perf_counter()
                        self._step_anchor_time = current_time
                        self._step_count = 0
                        self._suppress_next_drift_reset = True
                        self._clock_generator.suppress_next_drift_reset()
                        logger.debug(
                            f"BPM changed during apply {old_bpm} → {self.state.bpm}, "
                            "anchors reset (drift suppression enabled)"
                        )

                    # Send updated track info for Monitor display
                    await self._publisher.send_tracks(self._get_tracks_info())

                # === New destination-based architecture ===
                # Process messages from MessageScheduler (if loaded)
                if self._destinations_loaded and self._message_scheduler.message_count > 0:
                    current_step = self.state.position.step
                    scheduled_messages = self._message_scheduler.get_messages_at_step(current_step)

                    if scheduled_messages:
                        logger.debug(
                            f"Step {current_step}: sending {len(scheduled_messages)} "
                            "scheduled messages via destination router"
                        )

                        # Apply extension hooks (e.g., cps injection)
                        # Extensions modify messages just before sending
                        for hook in self._before_send_hooks:
                            scheduled_messages = hook(
                                scheduled_messages,
                                self.state.bpm,
                                current_step
                            )

                        self._destination_router.send_messages(scheduled_messages)

                # === Legacy StepProcessor (keep for compatibility) ===
                # Process current step (delegated to StepProcessor)
                # Uses Output IR (Layer 3) for OSC/MIDI events
                step_output = self._step_processor.process_step_v2(self.state)

                # Send OSC events to SuperDirt
                for osc_event in step_output.osc_events:
                    self._osc.send_osc_event(osc_event)

                # Schedule MIDI notes
                for midi_note in step_output.midi_notes:
                    if self._midi_enabled:
                        # Convert duration_ms back to gate for NoteScheduler
                        # gate = duration_ms / 1000 / step_duration
                        gate = midi_note.duration_ms / 1000.0 / step_duration
                        self._note_scheduler.schedule_note_on_channel(
                            midi_note.channel,
                            midi_note.note,
                            midi_note.velocity,
                            step_duration,
                            gate,
                        )

                # Send MIDI CC events
                for midi_cc in step_output.midi_ccs:
                    if self._midi_enabled and self._midi.is_connected:
                        self._midi.send_cc(midi_cc.channel, midi_cc.cc, midi_cc.value)

                # Send MIDI Pitch Bend events
                for pitch_bend in step_output.midi_pitch_bends:
                    if self._midi_enabled and self._midi.is_connected:
                        self._midi.send_pitch_bend(pitch_bend.channel, pitch_bend.value)

                # Send MIDI Aftertouch events
                for aftertouch in step_output.midi_aftertouches:
                    if self._midi_enabled and self._midi.is_connected:
                        self._midi.send_aftertouch(aftertouch.channel, aftertouch.value)

                # Publish position on beat boundaries (quarter notes) to reduce traffic
                if self.state.position.step % 4 == 0:
                    await self._publisher.send_position(
                        self.state.position.to_dict(),
                        bpm=self.state.bpm,
                        transport=self.state.playback_state.value,
                    )

                # Send tracks info at bar boundaries for Monitor page sync
                if self.state.position.step % 16 == 0:
                    await self._publisher.send_tracks(self._get_tracks_info())

            except Exception as e:
                logger.error(f"Step processing error: {e}\n{traceback.format_exc()}")
                await self._publisher.send_error("STEP_ERROR", str(e))

            # Advance step count and position
            self._step_count += 1
            self.state.advance_step()

            # Drift-corrected wait: calculate expected time for next step
            expected_next = self._step_anchor_time + (self._step_count * step_duration)
            wait_time = max(0, expected_next - time.perf_counter())
            await asyncio.sleep(wait_time)

    async def _handle_drift_reset(self, drift_ms: float, current_time: float) -> None:
        """
        Handle large clock drift by resetting the anchor.

        Instead of catching up (which causes burst playback),
        reset the anchor to current time and continue from there.
        This is inspired by Tidal's clockSkipTicks mechanism.

        Args:
            drift_ms: Detected drift in milliseconds (positive = behind, negative = ahead)
            current_time: Current perf_counter time
        """
        step_duration = self.state.step_duration

        # Calculate how many steps would be skipped
        skipped_steps = int(abs(drift_ms) / (step_duration * 1000))

        # Determine drift direction for logging
        direction = "behind" if drift_ms > 0 else "ahead"

        logger.warning(
            f"Clock drift reset: {drift_ms:.1f}ms {direction}, "
            f"skipping ~{skipped_steps} steps (threshold: {self.DRIFT_RESET_THRESHOLD_MS}ms)"
        )

        # Update statistics
        self._drift_stats["reset_count"] = int(self._drift_stats["reset_count"]) + 1
        self._drift_stats["total_skipped_steps"] = (
            int(self._drift_stats["total_skipped_steps"]) + skipped_steps
        )
        self._drift_stats["last_reset_drift_ms"] = drift_ms

        # Reset anchor to current time
        self._step_anchor_time = current_time
        self._step_count = 0

        # Notify API about the drift reset
        await self._publisher.send_error(
            "CLOCK_DRIFT_RESET",
            f"Clock resynchronized (drift: {drift_ms:.1f}ms {direction}, skipped: ~{skipped_steps} steps)"
        )

    def get_drift_stats(self) -> dict[str, float | int]:
        """
        Get drift correction statistics for monitoring.

        Returns:
            Dictionary with drift statistics:
            - reset_count: Number of times anchor was reset
            - max_drift_ms: Maximum drift observed
            - total_skipped_steps: Approximate total steps skipped
            - last_reset_drift_ms: Drift value at last reset
            - current_step_count: Current step count since last anchor
            - anchor_age_seconds: Time since anchor was set
        """
        return {
            **self._drift_stats,
            "current_step_count": self._step_count,
            "anchor_age_seconds": (
                time.perf_counter() - self._step_anchor_time
                if self._step_anchor_time else 0.0
            ),
        }

    async def _clock_loop(self) -> None:
        """24 PPQ MIDI clock loop (delegated to ClockGenerator)."""
        await self._clock_generator.run_clock_loop(
            self.state,
            lambda: self._running,
        )

    async def _note_off_loop(self) -> None:
        """
        Process pending note-off messages with adaptive sleep.

        Optimization inspired by TidalCycles' clockFrameTimespan:
        Instead of fixed 1ms polling (1000 calls/sec), sleep until
        the next note-off is due, with a maximum of 10ms wait.

        This reduces CPU usage significantly while maintaining
        note-off timing accuracy within 10ms (acceptable for MIDI).
        """
        NOTE_OFF_MAX_SLEEP: float = 0.010  # 10ms max wait

        while self._running:
            self._note_scheduler.process_pending_note_offs()

            # Adaptive sleep: wait until next note-off or max interval
            next_off_time = self._note_scheduler.get_next_off_time()
            if next_off_time is None:
                # No pending notes: use max sleep
                await asyncio.sleep(NOTE_OFF_MAX_SLEEP)
            else:
                # Calculate wait time, clamped to [1ms, 10ms]
                wait_time = next_off_time - time.perf_counter()
                wait_time = max(0.001, min(NOTE_OFF_MAX_SLEEP, wait_time))
                await asyncio.sleep(wait_time)

    # ================================================================
    # Status
    # ================================================================

    def _schedule_status_update(self) -> None:
        """Schedule status update if event loop is running."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.send_status())
        except RuntimeError:
            # No running event loop (e.g., in tests), skip
            pass

    def _schedule_tracks_update(self) -> None:
        """Schedule tracks update if event loop is running."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.send_tracks())
        except RuntimeError:
            # No running event loop (e.g., in tests), skip
            pass

    async def send_tracks(self) -> None:
        """Send track information to API for Monitor display"""
        tracks_info = self._get_tracks_info()
        logger.info(f"Sending tracks info: {len(tracks_info)} tracks")
        await self._publisher.send_tracks(tracks_info)

    def _get_tracks_info(self) -> list[dict[str, Any]]:
        """Build track info list for Monitor display (v5)"""
        tracks_info: list[dict[str, Any]] = []
        session = self.state.get_effective()

        for track_id, track in self.state.tracks.items():
            # Get sequence for this track
            sequence = session.sequences.get(track_id)
            events = list(sequence) if sequence else []

            tracks_info.append({
                "track_id": track_id,
                "sound": track.params.s or track_id,
                "pattern": self._events_to_pattern(events),
            })
        return tracks_info

    @staticmethod
    def _events_to_pattern(events: Any) -> str:
        """
        Convert events list to NibbleBeats pattern string (v5).

        Works with both v5 Event objects and legacy dict events.

        Example: [Event(step=0), Event(step=4), ...] → "x8888"
        """
        pattern = [0, 0, 0, 0]  # 4 nibbles = 16 steps
        for event in events:
            # Support both v5 Event objects and legacy dicts
            step = getattr(event, "step", None)
            if step is None:
                step = event.get("step", 0) if isinstance(event, dict) else 0

            if 0 <= step < 16:
                nibble_idx = step // 4
                bit_pos = 3 - (step % 4)
                pattern[nibble_idx] |= (1 << bit_pos)
        return 'x' + ''.join(format(n, 'x') for n in pattern)

    async def send_status(self) -> None:
        """Send current status to API"""
        await self._publisher.send_status(
            transport=self.state.playback_state.value,
            bpm=self.state.bpm,
            active_tracks=list(self.state.get_active_tracks().keys())
        )

    # ================================================================
    # Properties for backward compatibility
    # ================================================================

    @property
    def osc(self) -> OscOutput:
        """OSC output (for backward compatibility)"""
        return self._osc

    @property
    def midi(self) -> MidiOutput:
        """MIDI output (for backward compatibility)"""
        return self._midi

    @property
    def commands(self) -> CommandSource:
        """Command source (for backward compatibility)"""
        return self._commands

    @property
    def publisher(self) -> StateSink:
        """State sink (for backward compatibility)"""
        return self._publisher
