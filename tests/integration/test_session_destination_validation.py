"""
Integration tests for session destination validation.

Tests that LoopEngine validates destinations against DestinationRouter
before loading sessions.
"""

import pytest
from oiduna_loop.engine.loop_engine import LoopEngine
from oiduna_loop.tests.mocks import MockCommandSource, MockMidiOutput, MockOscOutput, MockStateSink
from oiduna_scheduler.scheduler_models import ScheduledMessageBatch, ScheduledMessage


class TestSessionDestinationValidation:
    """Integration tests for destination validation in session loading."""

    @pytest.fixture
    def engine(self):
        """Create a fresh LoopEngine instance with mock dependencies."""
        mock_osc = MockOscOutput()
        mock_midi = MockMidiOutput()
        mock_commands = MockCommandSource()
        mock_publisher = MockStateSink()

        engine = LoopEngine(
            osc=mock_osc,
            midi=mock_midi,
            command_consumer=mock_commands,
            state_producer=mock_publisher,
        )
        engine._register_handlers()
        return engine

    def test_session_with_unregistered_destination_fails(self, engine):
        """Session loading should fail if destination is not registered."""
        # Enable destinations (but don't register any)
        engine._session_loader._destinations_loaded = True

        # Create session with unregistered destination
        msg = ScheduledMessage(
            destination_id="nonexistent",
            cycle=0.0,
            step=0,
            params={"s": "bd"},
        )
        batch = ScheduledMessageBatch(
            messages=(msg,),
            bpm=120.0,
            pattern_length=4.0,
            destinations=frozenset({"nonexistent"}),
        )

        # Try to load session
        result = engine._session_loader.load_session(batch.to_dict())

        # Should fail with clear error message
        assert not result.success
        assert "unregistered destinations" in result.message.lower()
        assert "nonexistent" in result.message

    def test_session_with_registered_destination_succeeds(self, engine):
        """Session loading should succeed if all destinations are registered."""
        # Enable destinations and register one
        engine._session_loader._destinations_loaded = True
        engine._destination_router._senders["superdirt"] = None  # Mock sender

        # Create session with registered destination
        msg = ScheduledMessage(
            destination_id="superdirt",
            cycle=0.0,
            step=0,
            params={"s": "bd"},
        )
        batch = ScheduledMessageBatch(
            messages=(msg,),
            bpm=120.0,
            pattern_length=4.0,
            destinations=frozenset({"superdirt"}),
        )

        # Load session
        result = engine._session_loader.load_session(batch.to_dict())

        # Should succeed
        assert result.success

    def test_session_with_mixed_destinations_fails_if_any_unregistered(self, engine):
        """Session should fail if any destination is unregistered."""
        # Enable destinations and register only one
        engine._session_loader._destinations_loaded = True
        engine._destination_router._senders["superdirt"] = None  # Registered

        # Create session with both registered and unregistered destinations
        msg1 = ScheduledMessage(
            destination_id="superdirt",
            cycle=0.0,
            step=0,
            params={"s": "bd"},
        )
        msg2 = ScheduledMessage(
            destination_id="midi",  # Not registered
            cycle=1.0,
            step=64,
            params={"note": 60},
        )
        batch = ScheduledMessageBatch(
            messages=(msg1, msg2),
            bpm=120.0,
            pattern_length=4.0,
            destinations=frozenset({"superdirt", "midi"}),
        )

        # Try to load session
        result = engine._session_loader.load_session(batch.to_dict())

        # Should fail mentioning unregistered destination
        assert not result.success
        assert "unregistered destinations" in result.message.lower()
        assert "midi" in result.message

    def test_error_message_includes_registered_destinations(self, engine):
        """Error message should list registered destinations for troubleshooting."""
        # Enable destinations and register some
        engine._session_loader._destinations_loaded = True
        engine._destination_router._senders["superdirt"] = None
        engine._destination_router._senders["midi"] = None

        # Try to load session with unregistered destination
        msg = ScheduledMessage(
            destination_id="nonexistent",
            cycle=0.0,
            step=0,
            params={"s": "bd"},
        )
        batch = ScheduledMessageBatch(
            messages=(msg,),
            bpm=120.0,
            pattern_length=4.0,
            destinations=frozenset({"nonexistent"}),
        )

        result = engine._session_loader.load_session(batch.to_dict())

        # Error should mention registered destinations
        assert not result.success
        assert "registered destinations" in result.message.lower()
        # Should mention both registered destinations
        assert "superdirt" in result.message.lower() or "midi" in result.message.lower()

    def test_backward_compatibility_inferred_destinations(self, engine):
        """Session should validate even with inferred destinations (backward compat)."""
        # Enable destinations and register one
        engine._session_loader._destinations_loaded = True
        engine._destination_router._senders["superdirt"] = None

        # Create session dict WITHOUT destinations field (old format)
        session_dict = {
            "messages": [
                {
                    "destination_id": "superdirt",
                    "cycle": 0.0,
                    "step": 0,
                    "params": {"s": "bd"},
                },
            ],
            "bpm": 120.0,
            "pattern_length": 4.0,
            # No destinations field - should be inferred
        }

        # Load session
        result = engine._session_loader.load_session(session_dict)

        # Should succeed with inferred destinations
        assert result.success

    def test_empty_session_succeeds(self, engine):
        """Empty session with no destinations should succeed."""
        engine._session_loader._destinations_loaded = True

        batch = ScheduledMessageBatch(
            messages=(),
            bpm=120.0,
            pattern_length=4.0,
            destinations=frozenset(),
        )

        result = engine._session_loader.load_session(batch.to_dict())

        # Should succeed (no destinations to validate)
        assert result.success
