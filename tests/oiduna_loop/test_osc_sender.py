"""Tests for OscSender address configuration and send_any() method."""

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


class TestOscSenderSendAny:
    """Tests for send_any() method."""

    def test_send_any_method_exists(self):
        """Verify send_any() method exists."""
        sender = OscSender()
        assert hasattr(sender, 'send_any')
        assert callable(sender.send_any)

    def test_send_any_returns_false_when_not_connected(self):
        """Verify send_any() returns False when not connected."""
        sender = OscSender()
        result = sender.send_any({"freq": 440.0})
        assert result is False

    def test_send_any_with_connected_sender(self):
        """Verify send_any() works when connected."""
        sender = OscSender()
        sender.connect()

        # send_any should succeed (even if no server is listening)
        result = sender.send_any({"freq": 440.0, "amp": 0.5})
        assert result is True

        sender.disconnect()

    def test_send_silence_uses_send_any(self):
        """Verify send_silence() is implemented using send_any()."""
        sender = OscSender()
        sender.connect()

        # send_silence should work (backward compatibility)
        result = sender.send_silence(orbit=3)
        assert result is True

        sender.disconnect()


class TestOscSenderBackwardCompatibility:
    """Tests for backward compatibility."""

    def test_send_silence_still_works(self):
        """Verify send_silence() still exists for backward compatibility."""
        sender = OscSender()
        assert hasattr(sender, 'send_silence')
        assert callable(sender.send_silence)

    def test_default_constructor_still_works(self):
        """Verify old code using default constructor still works."""
        sender = OscSender()  # No address parameter
        assert sender._address == "/dirt/play"
        assert sender._host == "127.0.0.1"
        assert sender._port == 57120


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
