"""Tests for MIDI helper functions."""

import pytest
from oiduna.domain.models.midi_helpers import (
    MidiParams,
    MidiValidationError,
    validate_midi_params,
    is_valid_midi_params,
)


class TestMidiParams:
    """Test MidiParams TypedDict (type hints only)."""

    def test_basic_midi_params(self):
        """Test basic MIDI parameters with type hints."""
        params: MidiParams = {
            "note": 60,
            "velocity": 100,
            "duration_ms": 250,
            "channel": 0
        }
        assert params["note"] == 60
        assert params["velocity"] == 100

    def test_midi_params_with_cc(self):
        """Test MIDI parameters with CC."""
        params: MidiParams = {
            "note": 60,
            "cc": {1: 64, 7: 100}
        }
        assert params["cc"][1] == 64
        assert params["cc"][7] == 100

    def test_midi_params_with_nrpn(self):
        """Test MIDI parameters with NRPN."""
        params: MidiParams = {
            "note": 60,
            "nrpn": {256: 8192, 100: 16383}
        }
        assert params["nrpn"][256] == 8192
        assert params["nrpn"][100] == 16383


class TestValidateMidiParams:
    """Test MIDI parameter validation."""

    def test_valid_note(self):
        """Test valid note parameter."""
        validate_midi_params({"note": 60})
        validate_midi_params({"note": 0})
        validate_midi_params({"note": 127})

    def test_invalid_note(self):
        """Test invalid note parameter."""
        with pytest.raises(MidiValidationError, match="note must be 0-127"):
            validate_midi_params({"note": 128})

        with pytest.raises(MidiValidationError, match="note must be 0-127"):
            validate_midi_params({"note": -1})

        with pytest.raises(MidiValidationError, match="note must be 0-127"):
            validate_midi_params({"note": "60"})

    def test_valid_velocity(self):
        """Test valid velocity parameter."""
        validate_midi_params({"velocity": 100})
        validate_midi_params({"velocity": 0})
        validate_midi_params({"velocity": 127})

    def test_invalid_velocity(self):
        """Test invalid velocity parameter."""
        with pytest.raises(MidiValidationError, match="velocity must be 0-127"):
            validate_midi_params({"velocity": 128})

        with pytest.raises(MidiValidationError, match="velocity must be 0-127"):
            validate_midi_params({"velocity": -1})

    def test_valid_channel(self):
        """Test valid channel parameter."""
        validate_midi_params({"channel": 0})
        validate_midi_params({"channel": 15})

    def test_invalid_channel(self):
        """Test invalid channel parameter."""
        with pytest.raises(MidiValidationError, match="channel must be 0-15"):
            validate_midi_params({"channel": 16})

        with pytest.raises(MidiValidationError, match="channel must be 0-15"):
            validate_midi_params({"channel": -1})

    def test_valid_duration_ms(self):
        """Test valid duration_ms parameter."""
        validate_midi_params({"duration_ms": 1})
        validate_midi_params({"duration_ms": 250})
        validate_midi_params({"duration_ms": 10000})

    def test_invalid_duration_ms(self):
        """Test invalid duration_ms parameter."""
        with pytest.raises(MidiValidationError, match="duration_ms must be positive"):
            validate_midi_params({"duration_ms": 0})

        with pytest.raises(MidiValidationError, match="duration_ms must be positive"):
            validate_midi_params({"duration_ms": -100})

    def test_valid_cc(self):
        """Test valid CC parameter."""
        validate_midi_params({"cc": {1: 64}})
        validate_midi_params({"cc": {0: 0, 127: 127}})
        validate_midi_params({"cc": {7: 100, 10: 64}})

    def test_invalid_cc_type(self):
        """Test invalid CC parameter type."""
        with pytest.raises(MidiValidationError, match="cc must be dict"):
            validate_midi_params({"cc": [1, 64]})

    def test_invalid_cc_number(self):
        """Test invalid CC number."""
        with pytest.raises(MidiValidationError, match="CC number must be 0-127"):
            validate_midi_params({"cc": {128: 64}})

        with pytest.raises(MidiValidationError, match="CC number must be 0-127"):
            validate_midi_params({"cc": {-1: 64}})

    def test_invalid_cc_value(self):
        """Test invalid CC value."""
        with pytest.raises(MidiValidationError, match="CC value must be 0-127"):
            validate_midi_params({"cc": {1: 128}})

        with pytest.raises(MidiValidationError, match="CC value must be 0-127"):
            validate_midi_params({"cc": {1: -1}})

    def test_valid_nrpn(self):
        """Test valid NRPN parameter."""
        validate_midi_params({"nrpn": {0: 0}})
        validate_midi_params({"nrpn": {16383: 16383}})
        validate_midi_params({"nrpn": {256: 8192}})

    def test_invalid_nrpn_type(self):
        """Test invalid NRPN parameter type."""
        with pytest.raises(MidiValidationError, match="nrpn must be dict"):
            validate_midi_params({"nrpn": [256, 8192]})

    def test_invalid_nrpn_number(self):
        """Test invalid NRPN number."""
        with pytest.raises(MidiValidationError, match="NRPN number must be 0-16383"):
            validate_midi_params({"nrpn": {16384: 8192}})

        with pytest.raises(MidiValidationError, match="NRPN number must be 0-16383"):
            validate_midi_params({"nrpn": {-1: 8192}})

    def test_invalid_nrpn_value(self):
        """Test invalid NRPN value."""
        with pytest.raises(MidiValidationError, match="NRPN value must be 0-16383"):
            validate_midi_params({"nrpn": {256: 16384}})

        with pytest.raises(MidiValidationError, match="NRPN value must be 0-16383"):
            validate_midi_params({"nrpn": {256: -1}})

    def test_combined_params(self):
        """Test combined valid parameters."""
        params = {
            "note": 60,
            "velocity": 100,
            "channel": 0,
            "duration_ms": 250,
            "cc": {1: 64, 7: 100},
            "nrpn": {256: 8192}
        }
        validate_midi_params(params)  # Should not raise

    def test_empty_params(self):
        """Test empty params dict."""
        validate_midi_params({})  # Should not raise

    def test_unknown_params_ignored(self):
        """Test that unknown parameters are ignored."""
        params = {
            "note": 60,
            "custom_param": "anything",  # Unknown param
            "arbitrary_key": 999
        }
        validate_midi_params(params)  # Should not raise


class TestIsValidMidiParams:
    """Test is_valid_midi_params function."""

    def test_valid_params_returns_true(self):
        """Test that valid params return True."""
        assert is_valid_midi_params({"note": 60})
        assert is_valid_midi_params({"velocity": 100})
        assert is_valid_midi_params({"cc": {1: 64}})
        assert is_valid_midi_params({"nrpn": {256: 8192}})

    def test_invalid_params_returns_false(self):
        """Test that invalid params return False."""
        assert not is_valid_midi_params({"note": 200})
        assert not is_valid_midi_params({"velocity": -1})
        assert not is_valid_midi_params({"channel": 16})
        assert not is_valid_midi_params({"cc": {128: 64}})
        assert not is_valid_midi_params({"nrpn": {20000: 8192}})

    def test_empty_params_returns_true(self):
        """Test that empty params return True."""
        assert is_valid_midi_params({})
