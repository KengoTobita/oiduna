"""Tests for destination configuration models."""

import pytest
from pydantic import ValidationError

from destination_models import (
    OscDestinationConfig,
    MidiDestinationConfig,
)


class TestOscDestinationConfig:
    """Tests for OSC destination configuration validation."""

    def test_valid_config(self):
        """Test valid OSC configuration."""
        config = OscDestinationConfig(
            id="superdirt",
            type="osc",
            host="127.0.0.1",
            port=57120,
            address="/dirt/play"
        )
        assert config.id == "superdirt"
        assert config.host == "127.0.0.1"
        assert config.port == 57120
        assert config.address == "/dirt/play"
        assert config.use_bundle is False

    def test_default_host(self):
        """Test default host is 127.0.0.1."""
        config = OscDestinationConfig(
            id="test",
            port=57120,
            address="/test"
        )
        assert config.host == "127.0.0.1"

    def test_use_bundle_flag(self):
        """Test use_bundle flag."""
        config = OscDestinationConfig(
            id="test",
            port=57120,
            address="/test",
            use_bundle=True
        )
        assert config.use_bundle is True

    def test_invalid_port_too_low(self):
        """Test port validation - too low."""
        with pytest.raises(ValidationError) as exc_info:
            OscDestinationConfig(
                id="test",
                port=1023,  # Below 1024
                address="/test"
            )
        assert "port" in str(exc_info.value).lower()

    def test_invalid_port_too_high(self):
        """Test port validation - too high."""
        with pytest.raises(ValidationError) as exc_info:
            OscDestinationConfig(
                id="test",
                port=65536,  # Above 65535
                address="/test"
            )
        assert "port" in str(exc_info.value).lower()

    def test_invalid_address_no_slash(self):
        """Test address validation - missing leading slash."""
        with pytest.raises(ValidationError) as exc_info:
            OscDestinationConfig(
                id="test",
                port=57120,
                address="dirt/play"  # Missing /
            )
        assert "address" in str(exc_info.value).lower()

    def test_invalid_id_empty(self):
        """Test ID validation - empty string."""
        with pytest.raises(ValidationError) as exc_info:
            OscDestinationConfig(
                id="",
                port=57120,
                address="/test"
            )
        assert "id" in str(exc_info.value).lower()

    def test_invalid_id_special_chars(self):
        """Test ID validation - special characters."""
        with pytest.raises(ValidationError) as exc_info:
            OscDestinationConfig(
                id="test@destination",  # @ not allowed
                port=57120,
                address="/test"
            )
        assert "id" in str(exc_info.value).lower()

    def test_valid_id_with_underscore(self):
        """Test valid ID with underscore."""
        config = OscDestinationConfig(
            id="super_dirt",
            port=57120,
            address="/test"
        )
        assert config.id == "super_dirt"

    def test_valid_id_with_hyphen(self):
        """Test valid ID with hyphen."""
        config = OscDestinationConfig(
            id="super-dirt",
            port=57120,
            address="/test"
        )
        assert config.id == "super-dirt"


class TestMidiDestinationConfig:
    """Tests for MIDI destination configuration validation."""

    def test_valid_config(self):
        """Test valid MIDI configuration."""
        config = MidiDestinationConfig(
            id="volca_bass",
            type="midi",
            port_name="USB MIDI 1",
            default_channel=0
        )
        assert config.id == "volca_bass"
        assert config.port_name == "USB MIDI 1"
        assert config.default_channel == 0

    def test_default_channel_zero(self):
        """Test default channel defaults to 0."""
        config = MidiDestinationConfig(
            id="test",
            port_name="Test Port"
        )
        assert config.default_channel == 0

    def test_invalid_channel_too_low(self):
        """Test channel validation - too low."""
        with pytest.raises(ValidationError) as exc_info:
            MidiDestinationConfig(
                id="test",
                port_name="Test Port",
                default_channel=-1
            )
        assert "default_channel" in str(exc_info.value).lower()

    def test_invalid_channel_too_high(self):
        """Test channel validation - too high."""
        with pytest.raises(ValidationError) as exc_info:
            MidiDestinationConfig(
                id="test",
                port_name="Test Port",
                default_channel=16  # Max is 15
            )
        assert "default_channel" in str(exc_info.value).lower()

    def test_valid_channel_range(self):
        """Test all valid channel values 0-15."""
        for channel in range(16):
            config = MidiDestinationConfig(
                id=f"test_{channel}",
                port_name="Test Port",
                default_channel=channel
            )
            assert config.default_channel == channel

    def test_invalid_id_empty(self):
        """Test ID validation - empty string."""
        with pytest.raises(ValidationError) as exc_info:
            MidiDestinationConfig(
                id="",
                port_name="Test Port"
            )
        assert "id" in str(exc_info.value).lower()

    def test_invalid_id_special_chars(self):
        """Test ID validation - special characters."""
        with pytest.raises(ValidationError) as exc_info:
            MidiDestinationConfig(
                id="test device",  # Space not allowed
                port_name="Test Port"
            )
        assert "id" in str(exc_info.value).lower()

    def test_midi_port_warning_for_missing_port(self):
        """Test that missing MIDI port generates warning, not error."""
        # Should not raise - may warn if MIDI access is available
        config = MidiDestinationConfig(
            id="test",
            port_name="NonExistent Port 999"
        )
        assert config.port_name == "NonExistent Port 999"
