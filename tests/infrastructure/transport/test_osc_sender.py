"""Tests for OscSender.

Tests cover:
- Connection lifecycle
- Parameter conversion
- Send operations
- Error handling
- Boundary values
"""

import pytest

from oiduna.infrastructure.transport.osc_sender import OscSender


class TestConnectionLifecycle:
    """Test connection and disconnection."""

    def test_initial_state_not_connected(self, mock_osc_client):
        """Test that sender starts in disconnected state."""
        sender = OscSender()
        assert not sender.is_connected

    def test_connect_success(self, mock_osc_client):
        """Test successful connection."""
        sender = OscSender()
        sender.connect()

        assert sender.is_connected

    def test_connect_creates_client(self, mock_osc_client):
        """Test that connect creates OSC client."""
        sender = OscSender()
        sender.connect()

        client = mock_osc_client.get_client()
        assert client is not None
        assert client.host == OscSender.DEFAULT_HOST
        assert client.port == OscSender.DEFAULT_PORT

    def test_connect_with_custom_params(self, mock_osc_client):
        """Test connection with custom host and port."""
        sender = OscSender(host="192.168.1.100", port=9000, address="/custom/addr")
        sender.connect()

        client = mock_osc_client.get_client()
        assert client.host == "192.168.1.100"
        assert client.port == 9000

    def test_disconnect_clears_connection(self, mock_osc_client):
        """Test that disconnect clears connection state."""
        sender = OscSender()
        sender.connect()
        assert sender.is_connected

        sender.disconnect()

        assert not sender.is_connected

    def test_disconnect_without_connect(self, mock_osc_client):
        """Test that disconnect without connect does not error."""
        sender = OscSender()
        sender.disconnect()  # Should not raise

        assert not sender.is_connected

    def test_default_constants(self, mock_osc_client):
        """Test default constant values."""
        assert OscSender.DEFAULT_HOST == "127.0.0.1"
        assert OscSender.DEFAULT_PORT == 57120
        assert OscSender.DEFAULT_ADDRESS == "/dirt/play"


class TestParameterConversion:
    """Test parameter dictionary to OSC args conversion."""

    def test_send_simple_params(self, mock_osc_client):
        """Test sending simple parameters."""
        sender = OscSender()
        sender.connect()

        result = sender.send({"s": "bd", "gain": 0.8})

        assert result is True
        client = mock_osc_client.get_client()
        messages = client.get_messages()

        assert len(messages) == 1
        address, args = messages[0]
        assert address == "/dirt/play"
        assert args == ["s", "bd", "gain", 0.8]

    def test_send_multiple_params(self, mock_osc_client):
        """Test sending multiple parameters."""
        sender = OscSender()
        sender.connect()

        sender.send({"s": "sn", "n": 2, "gain": 0.5, "pan": 0.25})

        client = mock_osc_client.get_client()
        messages = client.get_messages()
        _, args = messages[0]

        # Args should alternate keys and values
        assert "s" in args and "sn" in args
        assert "n" in args and 2 in args
        assert "gain" in args and 0.5 in args
        assert "pan" in args and 0.25 in args

    def test_send_empty_params(self, mock_osc_client):
        """Test sending empty parameter dict."""
        sender = OscSender()
        sender.connect()

        result = sender.send({})

        assert result is True
        client = mock_osc_client.get_client()
        messages = client.get_messages()

        assert len(messages) == 1
        _, args = messages[0]
        assert args == []

    def test_send_unicode_params(self, mock_osc_client):
        """Test sending unicode string parameters."""
        sender = OscSender()
        sender.connect()

        sender.send({"s": "音楽", "name": "Ødúná 🎵"})

        client = mock_osc_client.get_client()
        messages = client.get_messages()
        _, args = messages[0]

        assert "音楽" in args
        assert "Ødúná 🎵" in args

    def test_send_special_chars(self, mock_osc_client):
        """Test sending parameters with special characters."""
        sender = OscSender()
        sender.connect()

        sender.send({"key": "value with spaces", "key2": "value!@#$%"})

        client = mock_osc_client.get_client()
        messages = client.get_messages()
        _, args = messages[0]

        assert "value with spaces" in args
        assert "value!@#$%" in args


class TestSendOperations:
    """Test send operation results."""

    def test_send_not_connected_returns_false(self, mock_osc_client):
        """Test send when not connected returns False."""
        sender = OscSender()

        result = sender.send({"s": "bd"})

        assert result is False

    def test_send_success_returns_true(self, mock_osc_client):
        """Test successful send returns True."""
        sender = OscSender()
        sender.connect()

        result = sender.send({"s": "bd"})

        assert result is True

    def test_send_multiple_messages(self, mock_osc_client):
        """Test sending multiple messages."""
        sender = OscSender()
        sender.connect()

        sender.send({"s": "bd"})
        sender.send({"s": "sn"})
        sender.send({"s": "hh"})

        client = mock_osc_client.get_client()
        messages = client.get_messages()

        assert len(messages) == 3

    def test_send_after_disconnect_returns_false(self, mock_osc_client):
        """Test send after disconnect returns False."""
        sender = OscSender()
        sender.connect()
        sender.disconnect()

        result = sender.send({"s": "bd"})

        assert result is False

    def test_send_exception_returns_false(self, mock_osc_client):
        """Test send handles exceptions and returns False."""
        sender = OscSender()
        sender.connect()

        client = mock_osc_client.get_client()
        client.inject_send_error(RuntimeError("Send failed"))

        result = sender.send({"s": "bd"})

        assert result is False


class TestBoundaryValues:
    """Test boundary value parameters."""

    def test_send_large_integer(self, mock_osc_client):
        """Test sending large integer values."""
        sender = OscSender()
        sender.connect()

        sender.send({"value": 2147483647})

        client = mock_osc_client.get_client()
        messages = client.get_messages()
        _, args = messages[0]

        assert 2147483647 in args

    def test_send_large_float(self, mock_osc_client):
        """Test sending large float values."""
        sender = OscSender()
        sender.connect()

        sender.send({"value": 3.4e38})

        client = mock_osc_client.get_client()
        messages = client.get_messages()
        _, args = messages[0]

        assert 3.4e38 in args

    def test_send_many_params(self, mock_osc_client):
        """Test sending many parameters (100+)."""
        sender = OscSender()
        sender.connect()

        params = {f"param_{i}": i for i in range(100)}
        result = sender.send(params)

        assert result is True
        client = mock_osc_client.get_client()
        messages = client.get_messages()
        _, args = messages[0]

        # Should have 200 args (100 keys + 100 values)
        assert len(args) == 200

    def test_send_negative_values(self, mock_osc_client):
        """Test sending negative numeric values."""
        sender = OscSender()
        sender.connect()

        sender.send({"int": -42, "float": -3.14})

        client = mock_osc_client.get_client()
        messages = client.get_messages()
        _, args = messages[0]

        assert -42 in args
        assert -3.14 in args

    def test_send_zero_values(self, mock_osc_client):
        """Test sending zero values."""
        sender = OscSender()
        sender.connect()

        sender.send({"int": 0, "float": 0.0})

        client = mock_osc_client.get_client()
        messages = client.get_messages()
        _, args = messages[0]

        assert 0 in args
        assert 0.0 in args

    def test_send_boolean_values(self, mock_osc_client):
        """Test sending boolean values."""
        sender = OscSender()
        sender.connect()

        sender.send({"enabled": True, "disabled": False})

        client = mock_osc_client.get_client()
        messages = client.get_messages()
        _, args = messages[0]

        assert True in args
        assert False in args

    def test_send_none_value(self, mock_osc_client):
        """Test sending None value."""
        sender = OscSender()
        sender.connect()

        sender.send({"value": None})

        client = mock_osc_client.get_client()
        messages = client.get_messages()
        _, args = messages[0]

        assert None in args


class TestCustomAddress:
    """Test custom OSC address."""

    def test_custom_address_used(self, mock_osc_client):
        """Test that custom address is used for messages."""
        sender = OscSender(address="/custom/path")
        sender.connect()

        sender.send({"s": "bd"})

        client = mock_osc_client.get_client()
        messages = client.get_messages()
        address, _ = messages[0]

        assert address == "/custom/path"

    def test_different_addresses(self, mock_osc_client):
        """Test creating senders with different addresses."""
        sender1 = OscSender(address="/addr1")
        sender2 = OscSender(address="/addr2")

        sender1.connect()
        sender2.connect()

        sender1.send({"msg": 1})
        sender2.send({"msg": 2})

        # Get both clients
        clients = mock_osc_client.get_all_clients()
        assert len(clients) == 2

        msg1 = clients[0].get_messages()[0]
        msg2 = clients[1].get_messages()[0]

        assert msg1[0] == "/addr1"
        assert msg2[0] == "/addr2"
