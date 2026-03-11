"""
Oiduna Loop Engine

Main loop engine that orchestrates:
- Step sequencer (16th notes)
- MIDI clock (24 PPQ)
- OSC output to SuperDirt
- MIDI output
- In-process IPC with oiduna_api

Refactored using Martin Fowler patterns:
- Extract Class: NoteScheduler, ClockGenerator
- Single Responsibility Principle
- Dependency Injection: Protocol-based DI for testability
"""

from __future__ import annotations

import asyncio
import logging
import time
import traceback
from typing import Any
from collections.abc import Callable

from pydantic import ValidationError

from ..commands import (
    BpmCommand,
    MidiPanicCommand,
    MidiPortCommand,
    MuteCommand,
    PanicCommand,
    PauseCommand,
    PlayCommand,
    SoloCommand,
    StopCommand,
)
from ..protocols import (
    CommandConsumer,
    MidiOutput,
    OscOutput,
    StateProducer,
)
from ..result import CommandResult
from ..state import PlaybackState, RuntimeState
from .clock_generator import ClockGenerator
from .command_handler import CommandHandler
from .note_scheduler import NoteScheduler
from .session_loader import SessionLoader
# New destination-based architecture imports
from pathlib import Path

from oiduna_scheduler.scheduler_models import LoopSchedule, ScheduleEntry
from oiduna_scheduler.scheduler import LoopScheduler
from oiduna_scheduler.router import DestinationRouter
from oiduna_scheduler.senders import OscDestinationSender, MidiDestinationSender
from oiduna_models import OscDestinationConfig, MidiDestinationConfig
from oiduna_models import load_destinations_from_file
from oiduna_timeline import CuedChangeTimeline

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

    # Timeline lookahead configuration (ADR-0020)
    # Apply timeline changes N steps ahead to avoid blocking critical path
    TIMELINE_LOOKAHEAD_STEPS: int = 32  # 2 bar lookahead (~8sec @ BPM 120)
    TIMELINE_MIN_LOOKAHEAD: int = 8     # 2 beat minimum (~2sec @ BPM 120)

    def __init__(
        self,
        osc: OscOutput,
        midi: MidiOutput,
        command_consumer: CommandConsumer,
        state_producer: StateProducer,
        before_send_hooks: list[Callable[[list[ScheduleEntry], float, int], list[ScheduleEntry]]] | None = None,
    ):
        """
        Initialize LoopEngine with injected dependencies.

        Args:
            osc: OSC output (OscSender or mock)
            midi: MIDI output (MidiSender or mock)
            command_consumer: Command consumer (receives commands from API).
            state_producer: State producer (sends state to API).
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
        self._command_consumer = command_consumer
        self._state_producer = state_producer

        # Processors (Martin Fowler: Extract Class)
        self._note_scheduler = NoteScheduler(self._midi)
        self._clock_generator = ClockGenerator(self._midi)

        # Command handler (extracted for Single Responsibility Principle)
        self._command_handler: CommandHandler | None = None  # Initialized after state setup

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

        # Timeline scheduling (cumulative step counter, persists across stop/start)
        self._global_step: int = 0
        self._timeline: CuedChangeTimeline | None = None

        # New destination-based architecture (Milestone 3)
        self._loop_scheduler = LoopScheduler()
        self._destination_router = DestinationRouter()

        # Session loader (extracted for SRP)
        self._session_loader = SessionLoader(
            destination_router=self._destination_router,
            message_scheduler=self._loop_scheduler,
            state=self.state,
            status_update_callback=self._schedule_status_update,
        )

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
        self._command_consumer.connect()
        self._state_producer.connect()

        # Initialize command handler BEFORE registering handlers
        if self._command_handler is None:
            self._command_handler = CommandHandler(
                state=self.state,
                clock_generator=self._clock_generator,
                note_scheduler=self._note_scheduler,
                publisher=self._state_producer,
                midi_enabled=self._midi_enabled,
            )

        # Register command handlers
        self._register_handlers()

        # Load destination configurations (new architecture)
        self._session_loader.load_destinations()

        logger.info("Loop engine started")

    def stop(self) -> None:
        """Stop the loop engine"""
        self._running = False

        # Stop playback if not already stopped
        if self.state.playback_state != PlaybackState.STOPPED:
            self.handle_stop({})

        # Disconnect
        self._osc.disconnect()
        self._midi.disconnect()
        self._command_consumer.disconnect()
        self._state_producer.disconnect()

        logger.info("Loop engine stopped")

    def _register_handlers(self) -> None:
        """Register command handlers"""
        # Initialize command handler if not already done (for tests)
        if self._command_handler is None:
            self._command_handler = CommandHandler(
                state=self.state,
                clock_generator=self._clock_generator,
                note_scheduler=self._note_scheduler,
                publisher=self._state_producer,
                midi_enabled=self._midi_enabled,
            )

        # Session loading (delegated to SessionLoader)
        self._command_consumer.register_handler("session", self._session_loader.load_session)

        # Playback commands (delegated to CommandHandler via wrappers)
        self._command_consumer.register_handler("play", self._command_handler.handle_play)
        self._command_consumer.register_handler("stop", self._command_handler.handle_stop)
        self._command_consumer.register_handler("pause", self._command_handler.handle_pause)
        self._command_consumer.register_handler("mute", self._command_handler.handle_mute)
        self._command_consumer.register_handler("solo", self._command_handler.handle_solo)
        self._command_consumer.register_handler("bpm", self._command_handler.handle_bpm)
        self._command_consumer.register_handler("panic", self._handle_panic)  # Uses wrapper for additional logic

        # MIDI-specific commands (remain in LoopEngine - need access to _midi)
        self._command_consumer.register_handler("midi_port", self._handle_midi_port)
        self._command_consumer.register_handler("midi_panic", self._handle_midi_panic)

    # ================================================================
    # Command Handlers
    # ================================================================

    def handle_play(self, payload: dict[str, Any]) -> CommandResult:
        """
        Start or resume playback (like video player play button).

        Public API for playback control - can be called directly from routes.
        Wrapper around CommandHandler with additional engine-specific logic.
        """
        # Remember state before change
        old_state = self.state.playback_state

        # Delegate to command handler
        result = self._command_handler.handle_play(payload)

        if result.success and old_state != PlaybackState.PLAYING:
            # Send appropriate MIDI clock message (engine-specific)
            if self._midi_enabled:
                if old_state == PlaybackState.STOPPED:
                    self._clock_generator.send_start()
                elif old_state == PlaybackState.PAUSED:
                    self._clock_generator.send_continue()

            # Send status and tracks update (non-blocking)
            self._schedule_status_update()
            self._schedule_tracks_update()

        return result

    def handle_stop(self, payload: dict[str, Any]) -> CommandResult:
        """
        Stop playback and reset to beginning (like video player stop button).

        Public API for playback control - can be called directly from routes.
        Wrapper around CommandHandler with additional engine-specific logic.
        """
        # Remember state before change
        was_playing = self.state.playback_state == PlaybackState.PLAYING

        # Delegate to command handler
        result = self._command_handler.handle_stop(payload)

        if result.success:
            # Clear note scheduler (engine-specific)
            self._note_scheduler.clear_all()

            # Send MIDI stop if was playing (engine-specific)
            if was_playing and self._midi_enabled:
                self._clock_generator.send_stop()

            # Reset drift correction anchor (engine-specific)
            self._step_anchor_time = None
            self._step_count = 0
            # NOTE: _global_step is NOT reset - it's a cumulative counter
            # that persists across stop/start for timeline scheduling

            # Send status update (non-blocking)
            self._schedule_status_update()

        return result

    def handle_pause(self, payload: dict[str, Any]) -> CommandResult:
        """
        Pause playback, maintaining position (like video player pause button).

        Public API for playback control - can be called directly from routes.
        Wrapper around CommandHandler with additional engine-specific logic.
        """
        # Delegate to command handler
        result = self._command_handler.handle_pause(payload)

        if result.success:
            # Clear note scheduler (engine-specific)
            self._note_scheduler.clear_all()

            # Send MIDI stop (enables proper resume with CONTINUE)
            if self._midi_enabled:
                self._clock_generator.send_stop()

            # Reset drift correction anchor (engine-specific)
            # Will re-anchor when playback resumes
            self._step_anchor_time = None

            # Send status update (non-blocking)
            self._schedule_status_update()

        return result

    def _handle_mute(self, payload: dict[str, Any]) -> CommandResult:
        """Mute/unmute a track - delegates to CommandHandler"""
        return self._command_handler.handle_mute(payload)

    def _handle_solo(self, payload: dict[str, Any]) -> CommandResult:
        """Solo/unsolo a track - delegates to CommandHandler"""
        return self._command_handler.handle_solo(payload)

    def _handle_bpm(self, payload: dict[str, Any]) -> CommandResult:
        """
        Change BPM with proper anchor reset for smooth transitions.

        Wrapper around CommandHandler with engine-specific drift anchor reset logic.
        """
        # Delegate to command handler
        result = self._command_handler.handle_bpm(payload)

        if result.success:
            # Reset anchors during playback to prevent false drift detection
            # (engine-specific timing logic)
            if self.state.playing and self._step_anchor_time is not None:
                current_time = time.perf_counter()
                self._step_anchor_time = current_time
                self._step_count = 0

                # Suppress the next drift reset notification (flag-based, not time-based)
                # This avoids race conditions with async timing
                self._suppress_next_drift_reset = True

                # Also reset MIDI clock anchor with suppression
                self._clock_generator.suppress_next_drift_reset()

                logger.debug("Anchors reset after BPM change (drift suppression enabled)")

        return result

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
        # Delegate to command handler
        result = self._command_handler.handle_panic(payload)

        if result.success:
            # Silence all MIDI notes (engine-specific)
            self._silence_all_notes()

            # Stop playback and reset position
            self.state.reset_position()
            self.state.playback_state = PlaybackState.STOPPED

            # Reset drift correction anchor
            self._step_anchor_time = None
            self._step_count = 0

            logger.warning("PANIC: Emergency stop executed")
            self._schedule_status_update()

        return result

    # ================================================================
    # Public API Methods
    # ================================================================

    def play(self) -> CommandResult:
        """
        Public API: Start or resume playback.

        Returns:
            CommandResult indicating success or failure
        """
        return self.handle_play({})

    def stop_playback(self) -> CommandResult:
        """
        Public API: Stop playback and reset position.

        Returns:
            CommandResult indicating success or failure
        """
        return self.handle_stop({})

    def pause(self) -> CommandResult:
        """
        Public API: Pause playback at current position.

        Returns:
            CommandResult indicating success or failure
        """
        return self.handle_pause({})

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

    def set_timeline(self, timeline: CuedChangeTimeline) -> None:
        """
        Public API: Set the timeline for scheduled changes.

        Args:
            timeline: The ScheduledChangeTimeline instance to use for pattern changes.

        Example:
            >>> from oiduna_timeline import CuedChangeTimeline
            >>> timeline = CuedChangeTimeline()
            >>> engine.set_timeline(timeline)
        """
        self._timeline = timeline

    def get_global_step(self) -> int:
        """
        Public API: Get the current global step counter.

        The global step is a cumulative counter that persists across
        stop/start cycles, used for timeline scheduling.

        Returns:
            Current global step (0-based, starts at 0 on engine creation).
        """
        return self._global_step

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
                await self._state_producer.send_error(
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
        await self._state_producer.send("heartbeat", {
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
                processed = await self._command_consumer.process_commands()
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

        Uses ScheduleEntry architecture for event routing.
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

            # Execute current step: get messages, filter, apply hooks, send
            await self._execute_current_step()

            # Wait for next step with drift correction
            await self._wait_for_next_step()

    def _get_filtered_messages(self, current_step: int) -> list[ScheduleEntry]:
        """
        Get and filter messages for current step.

        Returns:
            Filtered list of ScheduleEntry for current step
        """
        if not self._session_loader.destinations_loaded or self._loop_scheduler.message_count == 0:
            return []

        scheduled_messages = self._loop_scheduler.get_messages_at_step(current_step)
        if not scheduled_messages:
            return []

        # Filter by mute/solo state
        return self.state.filter_messages(scheduled_messages)

    def _apply_hooks(
        self, messages: list[ScheduleEntry], current_step: int
    ) -> list[ScheduleEntry]:
        """
        Apply extension hooks to messages.

        Args:
            messages: List of scheduled messages
            current_step: Current step number

        Returns:
            Modified messages after applying all hooks
        """
        for hook in self._before_send_hooks:
            messages = hook(messages, self.state.bpm, current_step)
        return messages

    def _send_messages(self, messages: list[ScheduleEntry], current_step: int) -> None:
        """
        Send messages to destination router.

        Args:
            messages: List of scheduled messages to send
            current_step: Current step number (for logging)
        """
        if messages:
            logger.debug(
                f"Step {current_step}: sending {len(messages)} "
                "scheduled messages via destination router"
            )
            self._destination_router.send_messages(messages)

    async def _publish_periodic_updates(self, current_step: int) -> None:
        """
        Publish periodic updates (position, tracks info).

        Args:
            current_step: Current step number
        """
        # Publish position based on configured interval
        # "beat": every 4 steps (quarter note)
        # "bar": every 16 steps (full bar)
        interval = 16 if self.state.position_update_interval == "bar" else 4
        if current_step % interval == 0:
            await self._state_producer.send_position(
                self.state.position.to_dict(),
                bpm=self.state.bpm,
                transport=self.state.playback_state.value,
            )

        # Send tracks info at bar boundaries for Monitor page sync
        if current_step % 16 == 0:
            await self._state_producer.send_tracks(self._get_tracks_info())

    async def _execute_current_step(self) -> None:
        """Execute processing for current step."""
        try:
            current_step = self.state.position.step

            # Apply timeline changes with lookahead (ADR-0020)
            # Load messages N steps ahead to avoid blocking critical path
            if self._timeline:
                future_global_step = self._global_step + self.TIMELINE_LOOKAHEAD_STEPS
                from oiduna_loop.engine.timeline_loader import TimelineLoader
                TimelineLoader.apply_changes_at_step(
                    future_global_step,
                    self._timeline,
                    self._loop_scheduler,
                )

            # Get and filter messages (already prepared by lookahead)
            messages = self._get_filtered_messages(current_step)

            if messages:
                # Apply extension hooks
                messages = self._apply_hooks(messages, current_step)
                # Send to destination router
                self._send_messages(messages, current_step)

            # Publish periodic updates
            await self._publish_periodic_updates(current_step)

        except Exception as e:
            logger.error(f"Step processing error: {e}\n{traceback.format_exc()}")
            await self._state_producer.send_error("STEP_ERROR", str(e))

    async def _wait_for_next_step(self) -> None:
        """
        Wait for next step with drift correction.

        Advances step count and position, then waits until expected time.
        """
        # Advance step count and position
        self._step_count += 1
        self._global_step += 1  # Global step also increments (cumulative counter)
        self.state.advance_step()

        # Drift-corrected wait: calculate expected time for next step
        step_duration = self.state.step_duration
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
        await self._state_producer.send_error(
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
        await self._state_producer.send_tracks(tracks_info)

    def _get_tracks_info(self) -> list[dict[str, Any]]:
        """
        Build track info list for Monitor display.

        Note: After Phase 1-8 architecture unification, track/sequence structure
        no longer exists in RuntimeState. This method returns empty list.
        Monitor display should be updated to work with LoopSchedule architecture.
        """
        # Legacy CompiledSession architecture removed - return empty list
        return []

    @staticmethod
    def _events_to_pattern(events: Any) -> str:
        """
        Convert events list to NibbleBeats pattern string (v5).

        Example: [Event(step=0), Event(step=4), ...] → "x8888"
        """
        pattern = [0, 0, 0, 0]  # 4 nibbles = 16 steps
        for event in events:
            step = event.step

            if 0 <= step < 16:
                nibble_idx = step // 4
                bit_pos = 3 - (step % 4)
                pattern[nibble_idx] |= (1 << bit_pos)
        return 'x' + ''.join(format(n, 'x') for n in pattern)

    async def send_status(self) -> None:
        """Send current status to API"""
        await self._state_producer.send_status(
            transport=self.state.playback_state.value,
            bpm=self.state.bpm,
            active_tracks=self.state.get_active_track_ids()
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
        return self._command_consumer

    @property
    def publisher(self) -> StateSink:
        """State sink (for backward compatibility)"""
        return self._state_producer
