"""Tests for MessageScheduler."""

import pytest

from scheduler_models import ScheduledMessage, ScheduledMessageBatch
from scheduler import MessageScheduler


class TestMessageScheduler:
    """Tests for MessageScheduler class."""

    def test_init(self):
        """Test scheduler initialization."""
        scheduler = MessageScheduler()

        assert scheduler.message_count == 0
        assert scheduler.bpm == 120.0
        assert scheduler.pattern_length == 4.0
        assert len(scheduler.occupied_steps) == 0

    def test_load_single_message(self):
        """Test loading a single message."""
        msg = ScheduledMessage("dest1", 1.0, 0, {"s": "bd"})
        batch = ScheduledMessageBatch(messages=(msg,))

        scheduler = MessageScheduler()
        scheduler.load_messages(batch)

        assert scheduler.message_count == 1
        assert 0 in scheduler.occupied_steps

        messages = scheduler.get_messages_at_step(0)
        assert len(messages) == 1
        assert messages[0].destination_id == "dest1"

    def test_load_multiple_messages_same_step(self):
        """Test loading multiple messages at same step."""
        msg1 = ScheduledMessage("dest1", 1.0, 0, {"s": "bd"})
        msg2 = ScheduledMessage("dest2", 1.0, 0, {"s": "sn"})
        batch = ScheduledMessageBatch(messages=(msg1, msg2))

        scheduler = MessageScheduler()
        scheduler.load_messages(batch)

        assert scheduler.message_count == 2
        messages = scheduler.get_messages_at_step(0)
        assert len(messages) == 2

    def test_load_multiple_messages_different_steps(self):
        """Test loading messages at different steps."""
        msg1 = ScheduledMessage("dest1", 1.0, 0, {})
        msg2 = ScheduledMessage("dest1", 2.0, 16, {})
        msg3 = ScheduledMessage("dest1", 3.0, 32, {})
        batch = ScheduledMessageBatch(messages=(msg1, msg2, msg3))

        scheduler = MessageScheduler()
        scheduler.load_messages(batch)

        assert scheduler.message_count == 3
        assert scheduler.occupied_steps == {0, 16, 32}

        assert len(scheduler.get_messages_at_step(0)) == 1
        assert len(scheduler.get_messages_at_step(16)) == 1
        assert len(scheduler.get_messages_at_step(32)) == 1

    def test_get_messages_at_empty_step(self):
        """Test getting messages from step with no messages."""
        scheduler = MessageScheduler()
        messages = scheduler.get_messages_at_step(42)

        assert messages == []

    def test_load_replaces_existing_messages(self):
        """Test that load_messages replaces previous messages."""
        msg1 = ScheduledMessage("dest1", 1.0, 0, {})
        batch1 = ScheduledMessageBatch(messages=(msg1,))

        msg2 = ScheduledMessage("dest2", 1.0, 16, {})
        msg3 = ScheduledMessage("dest2", 2.0, 32, {})
        batch2 = ScheduledMessageBatch(messages=(msg2, msg3))

        scheduler = MessageScheduler()
        scheduler.load_messages(batch1)
        assert scheduler.message_count == 1
        assert 0 in scheduler.occupied_steps

        scheduler.load_messages(batch2)
        assert scheduler.message_count == 2
        assert 0 not in scheduler.occupied_steps
        assert scheduler.occupied_steps == {16, 32}

    def test_clear(self):
        """Test clearing scheduler."""
        msg = ScheduledMessage("dest1", 1.0, 0, {})
        batch = ScheduledMessageBatch(messages=(msg,))

        scheduler = MessageScheduler()
        scheduler.load_messages(batch)
        assert scheduler.message_count == 1

        scheduler.clear()
        assert scheduler.message_count == 0
        assert len(scheduler.occupied_steps) == 0

    def test_bpm_and_pattern_length(self):
        """Test BPM and pattern length are stored."""
        batch = ScheduledMessageBatch(
            messages=(),
            bpm=140.0,
            pattern_length=8.0
        )

        scheduler = MessageScheduler()
        scheduler.load_messages(batch)

        assert scheduler.bpm == 140.0
        assert scheduler.pattern_length == 8.0

    def test_empty_batch(self):
        """Test loading empty batch."""
        batch = ScheduledMessageBatch(messages=())

        scheduler = MessageScheduler()
        scheduler.load_messages(batch)

        assert scheduler.message_count == 0
        assert len(scheduler.occupied_steps) == 0

    def test_high_step_numbers(self):
        """Test with high step numbers (0-255 range)."""
        msg1 = ScheduledMessage("dest1", 10.0, 200, {})
        msg2 = ScheduledMessage("dest1", 12.0, 255, {})
        batch = ScheduledMessageBatch(messages=(msg1, msg2))

        scheduler = MessageScheduler()
        scheduler.load_messages(batch)

        assert scheduler.message_count == 2
        assert 200 in scheduler.occupied_steps
        assert 255 in scheduler.occupied_steps
