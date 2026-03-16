"""Tests for StatePublisher.

Tests cover:
- Connection lifecycle
- Generic send operation
- Helper methods (send_position, send_status, send_error, send_tracks)
- Error handling
- Boundary cases
"""

import pytest
import zmq

from oiduna.infrastructure.ipc.state_publisher import StatePublisher


class TestConnectionLifecycle:
    """Test connection and disconnection."""

    def test_initial_state_not_connected(self, mock_zmq_context):
        """Test that publisher starts in disconnected state."""
        publisher = StatePublisher()
        assert not publisher.is_connected

    def test_connect_success(self, mock_zmq_context):
        """Test successful connection."""
        publisher = StatePublisher()
        publisher.connect()

        assert publisher.is_connected

    def test_connect_creates_socket(self, mock_zmq_context):
        """Test that connect creates a PUB socket."""
        publisher = StatePublisher()
        publisher.connect()

        sockets = mock_zmq_context.get_sockets()
        assert len(sockets) == 1
        assert sockets[0].is_bound

    def test_disconnect_clears_connection(self, mock_zmq_context):
        """Test that disconnect clears connection state."""
        publisher = StatePublisher()
        publisher.connect()
        assert publisher.is_connected

        publisher.disconnect()

        assert not publisher.is_connected

    def test_disconnect_closes_socket(self, mock_zmq_context):
        """Test that disconnect closes the socket."""
        publisher = StatePublisher()
        publisher.connect()

        sockets = mock_zmq_context.get_sockets()
        socket = sockets[0]

        publisher.disconnect()

        assert socket.is_closed

    def test_disconnect_without_connect(self, mock_zmq_context):
        """Test that disconnect without connect does not error."""
        publisher = StatePublisher()
        publisher.disconnect()  # Should not raise

        assert not publisher.is_connected

    def test_custom_port(self, mock_zmq_context):
        """Test connection with custom port."""
        publisher = StatePublisher(port=5560)
        publisher.connect()

        assert publisher.is_connected

    def test_default_port_constant(self, mock_zmq_context):
        """Test that default port is correctly set."""
        assert StatePublisher.DEFAULT_PORT == 5557


class TestGenericSend:
    """Test generic send method."""

    @pytest.mark.asyncio
    async def test_send_not_connected(self, mock_zmq_context):
        """Test send when not connected does nothing."""
        publisher = StatePublisher()

        # Should not raise
        await publisher.send("test", {"data": "value"})

    @pytest.mark.asyncio
    async def test_send_valid_message(self, mock_zmq_context):
        """Test sending a valid message."""
        publisher = StatePublisher()
        publisher.connect()

        await publisher.send("position", {"step": 0, "bar": 1})

        sockets = mock_zmq_context.get_sockets()
        sent = sockets[0].get_sent_messages()

        assert len(sent) == 1

        # Verify message can be deserialized
        from oiduna.infrastructure.ipc.serializer import IPCSerializer
        serializer = IPCSerializer()
        msg_type, payload = serializer.deserialize_message(sent[0])

        assert msg_type == "position"
        assert payload == {"step": 0, "bar": 1}

    @pytest.mark.asyncio
    async def test_send_multiple_messages(self, mock_zmq_context):
        """Test sending multiple messages."""
        publisher = StatePublisher()
        publisher.connect()

        await publisher.send("msg1", {"data": 1})
        await publisher.send("msg2", {"data": 2})
        await publisher.send("msg3", {"data": 3})

        sockets = mock_zmq_context.get_sockets()
        sent = sockets[0].get_sent_messages()

        assert len(sent) == 3

    @pytest.mark.asyncio
    async def test_send_empty_payload(self, mock_zmq_context):
        """Test sending message with empty payload."""
        publisher = StatePublisher()
        publisher.connect()

        await publisher.send("empty", {})

        sockets = mock_zmq_context.get_sockets()
        sent = sockets[0].get_sent_messages()

        assert len(sent) == 1

        from oiduna.infrastructure.ipc.serializer import IPCSerializer
        serializer = IPCSerializer()
        msg_type, payload = serializer.deserialize_message(sent[0])

        assert msg_type == "empty"
        assert payload == {}

    @pytest.mark.asyncio
    async def test_send_zmq_error(self, mock_zmq_context):
        """Test send handles ZMQ errors gracefully."""
        publisher = StatePublisher()
        publisher.connect()

        sockets = mock_zmq_context.get_sockets()
        socket = sockets[0]

        # Inject error
        socket.inject_send_error(zmq.ZMQError())

        # Should not raise
        await publisher.send("test", {"data": "value"})


class TestSendPosition:
    """Test send_position helper method."""

    @pytest.mark.asyncio
    async def test_send_position_basic(self, mock_zmq_context):
        """Test sending basic position update."""
        publisher = StatePublisher()
        publisher.connect()

        position = {"step": 4, "bar": 2, "beat": 1, "timestamp": 1234567.89}
        await publisher.send_position(position)

        sockets = mock_zmq_context.get_sockets()
        sent = sockets[0].get_sent_messages()

        assert len(sent) == 1

        from oiduna.infrastructure.ipc.serializer import IPCSerializer
        serializer = IPCSerializer()
        msg_type, payload = serializer.deserialize_message(sent[0])

        assert msg_type == "position"
        assert payload["step"] == 4
        assert payload["bar"] == 2
        assert payload["beat"] == 1
        assert payload["timestamp"] == 1234567.89

    @pytest.mark.asyncio
    async def test_send_position_with_bpm(self, mock_zmq_context):
        """Test sending position with BPM."""
        publisher = StatePublisher()
        publisher.connect()

        position = {"step": 0}
        await publisher.send_position(position, bpm=120.0)

        sockets = mock_zmq_context.get_sockets()
        sent = sockets[0].get_sent_messages()

        from oiduna.infrastructure.ipc.serializer import IPCSerializer
        serializer = IPCSerializer()
        msg_type, payload = serializer.deserialize_message(sent[0])

        assert payload["bpm"] == 120.0

    @pytest.mark.asyncio
    async def test_send_position_with_transport(self, mock_zmq_context):
        """Test sending position with transport state."""
        publisher = StatePublisher()
        publisher.connect()

        position = {"step": 0}
        await publisher.send_position(position, transport="playing")

        sockets = mock_zmq_context.get_sockets()
        sent = sockets[0].get_sent_messages()

        from oiduna.infrastructure.ipc.serializer import IPCSerializer
        serializer = IPCSerializer()
        msg_type, payload = serializer.deserialize_message(sent[0])

        assert payload["transport"] == "playing"

    @pytest.mark.asyncio
    async def test_send_position_with_all_params(self, mock_zmq_context):
        """Test sending position with all optional parameters."""
        publisher = StatePublisher()
        publisher.connect()

        position = {"step": 8, "bar": 3}
        await publisher.send_position(position, bpm=140.0, transport="playing")

        sockets = mock_zmq_context.get_sockets()
        sent = sockets[0].get_sent_messages()

        from oiduna.infrastructure.ipc.serializer import IPCSerializer
        serializer = IPCSerializer()
        msg_type, payload = serializer.deserialize_message(sent[0])

        assert payload["step"] == 8
        assert payload["bar"] == 3
        assert payload["bpm"] == 140.0
        assert payload["transport"] == "playing"


class TestSendStatus:
    """Test send_status helper method."""

    @pytest.mark.asyncio
    async def test_send_status_basic(self, mock_zmq_context):
        """Test sending status update."""
        publisher = StatePublisher()
        publisher.connect()

        await publisher.send_status("playing", 120.0, ["t1", "t2"])

        sockets = mock_zmq_context.get_sockets()
        sent = sockets[0].get_sent_messages()

        assert len(sent) == 1

        from oiduna.infrastructure.ipc.serializer import IPCSerializer
        serializer = IPCSerializer()
        msg_type, payload = serializer.deserialize_message(sent[0])

        assert msg_type == "status"
        assert payload["transport"] == "playing"
        assert payload["bpm"] == 120.0
        assert payload["active_tracks"] == ["t1", "t2"]

    @pytest.mark.asyncio
    async def test_send_status_stopped(self, mock_zmq_context):
        """Test sending stopped status."""
        publisher = StatePublisher()
        publisher.connect()

        await publisher.send_status("stopped", 120.0, [])

        sockets = mock_zmq_context.get_sockets()
        sent = sockets[0].get_sent_messages()

        from oiduna.infrastructure.ipc.serializer import IPCSerializer
        serializer = IPCSerializer()
        msg_type, payload = serializer.deserialize_message(sent[0])

        assert payload["transport"] == "stopped"
        assert payload["active_tracks"] == []

    @pytest.mark.asyncio
    async def test_send_status_many_tracks(self, mock_zmq_context):
        """Test sending status with many active tracks."""
        publisher = StatePublisher()
        publisher.connect()

        tracks = [f"track_{i}" for i in range(100)]
        await publisher.send_status("playing", 128.0, tracks)

        sockets = mock_zmq_context.get_sockets()
        sent = sockets[0].get_sent_messages()

        from oiduna.infrastructure.ipc.serializer import IPCSerializer
        serializer = IPCSerializer()
        msg_type, payload = serializer.deserialize_message(sent[0])

        assert len(payload["active_tracks"]) == 100


class TestSendError:
    """Test send_error helper method."""

    @pytest.mark.asyncio
    async def test_send_error_basic(self, mock_zmq_context):
        """Test sending error notification."""
        publisher = StatePublisher()
        publisher.connect()

        await publisher.send_error("COMPILE_ERROR", "Pattern compilation failed")

        sockets = mock_zmq_context.get_sockets()
        sent = sockets[0].get_sent_messages()

        assert len(sent) == 1

        from oiduna.infrastructure.ipc.serializer import IPCSerializer
        serializer = IPCSerializer()
        msg_type, payload = serializer.deserialize_message(sent[0])

        assert msg_type == "error_msg"
        assert payload["code"] == "COMPILE_ERROR"
        assert payload["message"] == "Pattern compilation failed"

    @pytest.mark.asyncio
    async def test_send_error_empty_message(self, mock_zmq_context):
        """Test sending error with empty message."""
        publisher = StatePublisher()
        publisher.connect()

        await publisher.send_error("ERROR", "")

        sockets = mock_zmq_context.get_sockets()
        sent = sockets[0].get_sent_messages()

        from oiduna.infrastructure.ipc.serializer import IPCSerializer
        serializer = IPCSerializer()
        msg_type, payload = serializer.deserialize_message(sent[0])

        assert payload["message"] == ""

    @pytest.mark.asyncio
    async def test_send_error_unicode(self, mock_zmq_context):
        """Test sending error with unicode characters."""
        publisher = StatePublisher()
        publisher.connect()

        await publisher.send_error("ERROR", "Failed: 音楽 🎵")

        sockets = mock_zmq_context.get_sockets()
        sent = sockets[0].get_sent_messages()

        from oiduna.infrastructure.ipc.serializer import IPCSerializer
        serializer = IPCSerializer()
        msg_type, payload = serializer.deserialize_message(sent[0])

        assert payload["message"] == "Failed: 音楽 🎵"


class TestSendTracks:
    """Test send_tracks helper method."""

    @pytest.mark.asyncio
    async def test_send_tracks_basic(self, mock_zmq_context):
        """Test sending track information."""
        publisher = StatePublisher()
        publisher.connect()

        tracks = [
            {"track_id": "t1", "sound": "bd", "pattern": "bd*4"},
            {"track_id": "t2", "sound": "sn", "pattern": "~ sn"},
        ]
        await publisher.send_tracks(tracks)

        sockets = mock_zmq_context.get_sockets()
        sent = sockets[0].get_sent_messages()

        assert len(sent) == 1

        from oiduna.infrastructure.ipc.serializer import IPCSerializer
        serializer = IPCSerializer()
        msg_type, payload = serializer.deserialize_message(sent[0])

        assert msg_type == "tracks"
        assert len(payload["tracks"]) == 2
        assert payload["tracks"][0]["track_id"] == "t1"
        assert payload["tracks"][1]["track_id"] == "t2"

    @pytest.mark.asyncio
    async def test_send_tracks_empty(self, mock_zmq_context):
        """Test sending empty track list."""
        publisher = StatePublisher()
        publisher.connect()

        await publisher.send_tracks([])

        sockets = mock_zmq_context.get_sockets()
        sent = sockets[0].get_sent_messages()

        from oiduna.infrastructure.ipc.serializer import IPCSerializer
        serializer = IPCSerializer()
        msg_type, payload = serializer.deserialize_message(sent[0])

        assert payload["tracks"] == []

    @pytest.mark.asyncio
    async def test_send_tracks_many(self, mock_zmq_context):
        """Test sending many tracks."""
        publisher = StatePublisher()
        publisher.connect()

        tracks = [{"track_id": f"t{i}", "sound": "bd"} for i in range(50)]
        await publisher.send_tracks(tracks)

        sockets = mock_zmq_context.get_sockets()
        sent = sockets[0].get_sent_messages()

        from oiduna.infrastructure.ipc.serializer import IPCSerializer
        serializer = IPCSerializer()
        msg_type, payload = serializer.deserialize_message(sent[0])

        assert len(payload["tracks"]) == 50


class TestBoundaryCases:
    """Test boundary conditions."""

    @pytest.mark.asyncio
    async def test_send_large_payload(self, mock_zmq_context):
        """Test sending message with large payload (1000+ keys)."""
        publisher = StatePublisher()
        publisher.connect()

        large_payload = {f"key_{i}": f"value_{i}" for i in range(1000)}
        await publisher.send("large", large_payload)

        sockets = mock_zmq_context.get_sockets()
        sent = sockets[0].get_sent_messages()

        assert len(sent) == 1

        from oiduna.infrastructure.ipc.serializer import IPCSerializer
        serializer = IPCSerializer()
        msg_type, payload = serializer.deserialize_message(sent[0])

        assert len(payload) == 1000

    @pytest.mark.asyncio
    async def test_send_rapid_messages(self, mock_zmq_context):
        """Test sending many rapid messages."""
        publisher = StatePublisher()
        publisher.connect()

        # Send 100 messages rapidly
        for i in range(100):
            await publisher.send("rapid", {"index": i})

        sockets = mock_zmq_context.get_sockets()
        sent = sockets[0].get_sent_messages()

        assert len(sent) == 100

    @pytest.mark.asyncio
    async def test_send_after_disconnect(self, mock_zmq_context):
        """Test that send after disconnect does nothing."""
        publisher = StatePublisher()
        publisher.connect()
        publisher.disconnect()

        # Should not raise
        await publisher.send("test", {"data": "value"})

        # No messages sent
        # (can't check this easily with mocks, but verifying no exception)

    @pytest.mark.asyncio
    async def test_multiple_connect_disconnect_cycles(self, mock_zmq_context):
        """Test multiple connect/disconnect cycles."""
        publisher = StatePublisher()

        for i in range(3):
            publisher.connect()
            assert publisher.is_connected

            await publisher.send("cycle", {"iteration": i})

            publisher.disconnect()
            assert not publisher.is_connected

    @pytest.mark.asyncio
    async def test_send_position_preserves_original_dict(self, mock_zmq_context):
        """Test that send_position doesn't modify the original position dict."""
        publisher = StatePublisher()
        publisher.connect()

        position = {"step": 0, "bar": 1}
        original_keys = set(position.keys())

        await publisher.send_position(position, bpm=120.0, transport="playing")

        # Original dict should not be modified
        assert set(position.keys()) == original_keys
        assert "bpm" not in position
        assert "transport" not in position
