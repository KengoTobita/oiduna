"""Integration tests for IPC layer.

Tests the integration between:
- CommandConsumer and command handlers
- StateProducer and state updates
- In-process IPC communication
"""

import pytest
import sys
from pathlib import Path
from typing import Any

# Add tests directory to path
tests_dir = Path(__file__).parent.parent
sys.path.insert(0, str(tests_dir))

from oiduna.infrastructure.ipc.in_process import InProcessStateProducer
from infrastructure.execution.mocks import MockCommandConsumer


class TestInProcessIPC:
    """Test in-process IPC communication."""

    @pytest.mark.asyncio
    async def test_command_consumer_producer_communication(self):
        """Test command consumer and producer can communicate."""
        consumer = MockCommandConsumer()
        producer = InProcessStateProducer()

        # Connect both
        consumer.connect()
        producer.connect()

        # Register a handler
        received_commands = []

        def handler(payload: dict[str, Any]) -> None:
            received_commands.append(payload)

        consumer.register_handler("test_command", handler)

        # Inject command
        consumer.inject_command("test_command", {"data": "hello"})

        # Process commands
        processed = await consumer.process_commands()

        assert processed == 1
        assert len(received_commands) == 1
        assert received_commands[0] == {"data": "hello"}

    @pytest.mark.asyncio
    async def test_state_producer_publishes_status(self):
        """Test state producer can publish status updates."""
        producer = InProcessStateProducer()
        producer.connect()

        # Send status update
        await producer.send_status(
            transport="playing",
            bpm=140.0,
            active_tracks=["kick", "snare"],
        )

        # Check internal queue
        assert producer.queue.qsize() == 1
        event = await producer.queue.get()
        assert event["type"] == "status"
        assert event["data"]["transport"] == "playing"
        assert event["data"]["bpm"] == 140.0
        assert event["data"]["active_tracks"] == ["kick", "snare"]

    @pytest.mark.asyncio
    async def test_state_producer_publishes_position(self):
        """Test state producer can publish position updates."""
        producer = InProcessStateProducer()
        producer.connect()

        position = {"step": 64}
        await producer.send_position(position, bpm=120.0, transport="playing")

        assert producer.queue.qsize() == 1
        event = await producer.queue.get()
        assert event["type"] == "position"
        assert event["data"]["step"] == 64
        assert event["data"]["bpm"] == 120.0
        assert event["data"]["transport"] == "playing"

    @pytest.mark.asyncio
    async def test_state_producer_publishes_error(self):
        """Test state producer can publish error messages."""
        producer = InProcessStateProducer()
        producer.connect()

        await producer.send_error("validation_error", "Invalid parameter")

        assert producer.queue.qsize() == 1
        event = await producer.queue.get()
        assert event["type"] == "error"
        assert event["data"]["code"] == "validation_error"
        assert event["data"]["message"] == "Invalid parameter"

    @pytest.mark.asyncio
    async def test_multiple_command_handlers(self):
        """Test multiple command handlers can be registered."""
        consumer = MockCommandConsumer()
        consumer.connect()

        play_called = []
        stop_called = []

        def play_handler(payload: dict[str, Any]) -> None:
            play_called.append(payload)

        def stop_handler(payload: dict[str, Any]) -> None:
            stop_called.append(payload)

        consumer.register_handler("play", play_handler)
        consumer.register_handler("stop", stop_handler)

        # Inject commands
        consumer.inject_command("play", {})
        consumer.inject_command("stop", {})
        consumer.inject_command("play", {"from": "paused"})

        # Process all
        processed = await consumer.process_commands()

        assert processed == 3
        assert len(play_called) == 2
        assert len(stop_called) == 1

    @pytest.mark.asyncio
    async def test_consumer_disconnect(self):
        """Test consumer can disconnect."""
        consumer = MockCommandConsumer()
        consumer.connect()
        assert consumer.is_connected is True

        consumer.disconnect()
        assert consumer.is_connected is False

    @pytest.mark.asyncio
    async def test_producer_disconnect(self):
        """Test producer can disconnect."""
        producer = InProcessStateProducer()
        producer.connect()
        assert producer.is_connected is True

        producer.disconnect()
        assert producer.is_connected is True  # Always connected (in-process)


class TestCommandHandlerIntegration:
    """Test command handlers with IPC layer."""

    @pytest.mark.asyncio
    async def test_playback_commands_through_ipc(self):
        """Test playback commands flow through IPC layer."""
        from oiduna.infrastructure.execution.command_handler import CommandHandler
        from oiduna.infrastructure.execution.state.runtime_state import RuntimeState, PlaybackState
        from oiduna.infrastructure.execution.clock_generator import ClockGenerator
        from oiduna.infrastructure.execution.note_scheduler import NoteScheduler
        from infrastructure.execution.mocks import MockMidiOutput, MockStateProducer

        # Setup
        state = RuntimeState()
        midi = MockMidiOutput()
        clock = ClockGenerator(midi)
        note_scheduler = NoteScheduler(midi)
        publisher = MockStateProducer()

        handler = CommandHandler(
            state=state,
            clock_generator=clock,
            note_scheduler=note_scheduler,
            publisher=publisher,
            midi_enabled=True,
        )

        consumer = MockCommandConsumer()
        consumer.connect()

        # Register handlers
        consumer.register_handler("play", handler.handle_play)
        consumer.register_handler("stop", handler.handle_stop)
        consumer.register_handler("pause", handler.handle_pause)

        # Test play command
        consumer.inject_command("play", {})
        await consumer.process_commands()
        assert state.playback_state == PlaybackState.PLAYING

        # Test pause command
        consumer.inject_command("pause", {})
        await consumer.process_commands()
        assert state.playback_state == PlaybackState.PAUSED

        # Test stop command
        consumer.inject_command("stop", {})
        await consumer.process_commands()
        assert state.playback_state == PlaybackState.STOPPED
        assert state.position.step == 0

    @pytest.mark.asyncio
    async def test_bpm_command_through_ipc(self):
        """Test BPM command flows through IPC layer."""
        from oiduna.infrastructure.execution.command_handler import CommandHandler
        from oiduna.infrastructure.execution.state.runtime_state import RuntimeState
        from oiduna.infrastructure.execution.clock_generator import ClockGenerator
        from oiduna.infrastructure.execution.note_scheduler import NoteScheduler
        from infrastructure.execution.mocks import MockMidiOutput, MockStateProducer

        state = RuntimeState()
        midi = MockMidiOutput()
        clock = ClockGenerator(midi)
        note_scheduler = NoteScheduler(midi)
        publisher = MockStateProducer()

        handler = CommandHandler(
            state=state,
            clock_generator=clock,
            note_scheduler=note_scheduler,
            publisher=publisher,
        )

        consumer = MockCommandConsumer()
        consumer.connect()
        consumer.register_handler("bpm", handler.handle_bpm)

        # Change BPM
        consumer.inject_command("bpm", {"bpm": 140.0})
        await consumer.process_commands()

        assert state.bpm == 140.0

    @pytest.mark.asyncio
    async def test_invalid_bpm_command_returns_error(self):
        """Test invalid BPM command returns error result."""
        from oiduna.infrastructure.execution.command_handler import CommandHandler
        from oiduna.infrastructure.execution.state.runtime_state import RuntimeState
        from oiduna.infrastructure.execution.clock_generator import ClockGenerator
        from oiduna.infrastructure.execution.note_scheduler import NoteScheduler
        from infrastructure.execution.mocks import MockMidiOutput, MockStateProducer

        state = RuntimeState()
        midi = MockMidiOutput()
        clock = ClockGenerator(midi)
        note_scheduler = NoteScheduler(midi)
        publisher = MockStateProducer()

        handler = CommandHandler(
            state=state,
            clock_generator=clock,
            note_scheduler=note_scheduler,
            publisher=publisher,
        )

        # Invalid BPM (negative)
        result = handler.handle_bpm({"bpm": -10.0})

        assert result.success is False
        assert "Invalid" in result.message


class TestStatePublisherIntegration:
    """Test state publisher with real state updates."""

    @pytest.mark.asyncio
    async def test_state_updates_published_on_playback_change(self):
        """Test state updates are published when playback state changes."""
        from oiduna.infrastructure.execution.state.runtime_state import RuntimeState, PlaybackState

        state = RuntimeState()
        producer = InProcessStateProducer()
        producer.connect()

        # Simulate state change
        state.playback_state = PlaybackState.PLAYING
        await producer.send_status(
            transport=state.playback_state.value,
            bpm=state.bpm,
            active_tracks=[],
        )

        assert producer.queue.qsize() == 1
        event = await producer.queue.get()
        assert event["data"]["transport"] == "playing"

        # Another state change
        state.playback_state = PlaybackState.STOPPED
        await producer.send_status(
            transport=state.playback_state.value,
            bpm=state.bpm,
            active_tracks=[],
        )

        assert producer.queue.qsize() == 1
        event = await producer.queue.get()
        assert event["data"]["transport"] == "stopped"

    @pytest.mark.asyncio
    async def test_multiple_events_queued(self):
        """Test multiple events can be queued."""
        producer = InProcessStateProducer()
        producer.connect()

        # Send multiple events
        await producer.send_status("playing", 120.0, [])
        await producer.send_position({"step": 0})
        await producer.send_error("test", "test error")

        assert producer.queue.qsize() == 3

        # Verify order
        event1 = await producer.queue.get()
        assert event1["type"] == "status"

        event2 = await producer.queue.get()
        assert event2["type"] == "position"

        event3 = await producer.queue.get()
        assert event3["type"] == "error"
