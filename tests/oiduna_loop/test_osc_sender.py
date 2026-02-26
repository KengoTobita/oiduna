"""Tests for OscSender address configuration."""

import pytest
from oiduna_loop.output.osc_sender import OscSender


class TestOscSenderAddress:
    """Tests for OscSender address parameter."""

    def test_default_address(self):
        """Verify default address is /dirt/play (SuperDirt)."""
        sender = OscSender()
        assert sender._address == "/dirt/play"

    def test_custom_address(self):
        """Verify custom address can be set."""
        sender = OscSender(address="/supernova/play")
        assert sender._address == "/supernova/play"

    def test_custom_address_with_host_port(self):
        """Verify address works with custom host/port."""
        sender = OscSender(
            host="192.168.1.100",
            port=57110,
            address="/s_new"
        )
        assert sender._host == "192.168.1.100"
        assert sender._port == 57110
        assert sender._address == "/s_new"


class TestOscSenderSend:
    """Tests for send() method."""

    def test_send_returns_false_when_not_connected(self):
        """Verify send() returns False when not connected."""
        sender = OscSender()
        result = sender.send({"s": "bd", "gain": 0.8})
        assert result is False

    def test_send_with_connected_sender(self):
        """Verify send() works when connected."""
        sender = OscSender()
        sender.connect()

        # send should succeed (even if no server is listening)
        result = sender.send({"s": "bd", "gain": 0.8, "pan": 0.5})
        assert result is True

        sender.disconnect()

    def test_default_constructor(self):
        """Verify default constructor sets correct defaults."""
        sender = OscSender()
        assert sender._address == "/dirt/play"
        assert sender._host == "127.0.0.1"
        assert sender._port == 57120


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
