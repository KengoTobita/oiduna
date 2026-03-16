"""Tests for OSC and MIDI protocol validators.

Tests cover:
- OSC validation: keys, values, types, ranges
- MIDI validation: notes, velocity, channels, CC, pitch bend
- Boundary values
- Error accumulation
"""

import pytest

from oiduna.domain.schedule.validators import (
    OscValidator,
    OscValidationResult,
    MidiValidator,
    MidiValidationResult,
)


class TestOscValidationResult:
    """Test OscValidationResult helper methods."""

    def test_success_creates_valid_result(self):
        """Test success() creates valid result."""
        result = OscValidationResult.success()

        assert result.is_valid is True
        assert result.errors == []

    def test_failure_creates_invalid_result(self):
        """Test failure() creates invalid result with errors."""
        errors = ["Error 1", "Error 2"]
        result = OscValidationResult.failure(errors)

        assert result.is_valid is False
        assert result.errors == errors


class TestMidiValidationResult:
    """Test MidiValidationResult helper methods."""

    def test_success_creates_valid_result(self):
        """Test success() creates valid result."""
        result = MidiValidationResult.success()

        assert result.is_valid is True
        assert result.errors == []

    def test_failure_creates_invalid_result(self):
        """Test failure() creates invalid result with errors."""
        errors = ["Error 1", "Error 2"]
        result = MidiValidationResult.failure(errors)

        assert result.is_valid is False
        assert result.errors == errors


class TestOscValidatorBasics:
    """Test basic OSC validation functionality."""

    def test_empty_params_valid(self):
        """Test that empty params dict is valid."""
        validator = OscValidator()

        result = validator.validate_message({})

        assert result.is_valid is True
        assert result.errors == []

    def test_valid_simple_message(self):
        """Test validation of simple valid message."""
        validator = OscValidator()

        result = validator.validate_message({"s": "bd", "gain": 0.8})

        assert result.is_valid is True
        assert result.errors == []

    def test_valid_types_accepted(self):
        """Test that all valid OSC types are accepted."""
        validator = OscValidator()

        result = validator.validate_message({
            "int_param": 42,
            "float_param": 3.14,
            "str_param": "hello",
            "bytes_param": b"data",
            "bool_param": True,
        })

        assert result.is_valid is True


class TestOscKeyValidation:
    """Test OSC key validation."""

    def test_empty_key_invalid(self):
        """Test that empty key is invalid."""
        validator = OscValidator()

        result = validator.validate_message({"": "value"})

        assert result.is_valid is False
        assert any("empty" in err.lower() for err in result.errors)

    @pytest.mark.parametrize("forbidden_char", [" ", "#", "*", ",", "?", "[", "]", "{", "}"])
    def test_forbidden_characters_invalid(self, forbidden_char):
        """Test that forbidden characters in keys are invalid."""
        validator = OscValidator()
        key = f"key{forbidden_char}name"

        result = validator.validate_message({key: "value"})

        assert result.is_valid is False
        assert any("forbidden" in err.lower() for err in result.errors)

    def test_valid_key_formats(self):
        """Test various valid key formats."""
        validator = OscValidator()

        result = validator.validate_message({
            "simple": 1,
            "camelCase": 2,
            "snake_case": 3,
            "with-dash": 4,
            "with.dot": 5,
        })

        assert result.is_valid is True


class TestOscValueValidation:
    """Test OSC value type and range validation."""

    def test_int32_range_valid(self):
        """Test that int32 range values are valid."""
        validator = OscValidator()

        result = validator.validate_message({
            "min": -2147483648,
            "max": 2147483647,
            "zero": 0,
        })

        assert result.is_valid is True

    def test_int32_below_min_invalid(self):
        """Test that values below int32 min are invalid."""
        validator = OscValidator()

        result = validator.validate_message({"value": -2147483649})

        assert result.is_valid is False
        assert any("int32 range" in err for err in result.errors)

    def test_int32_above_max_invalid(self):
        """Test that values above int32 max are invalid."""
        validator = OscValidator()

        result = validator.validate_message({"value": 2147483648})

        assert result.is_valid is False
        assert any("int32 range" in err for err in result.errors)

    def test_float32_range_valid(self):
        """Test that float32 range values are valid."""
        validator = OscValidator()

        result = validator.validate_message({
            "small": -3.4e38,
            "large": 3.4e38,
            "zero": 0.0,
            "pi": 3.14159,
        })

        assert result.is_valid is True

    def test_float32_below_min_invalid(self):
        """Test that values below float32 min are invalid."""
        validator = OscValidator()

        result = validator.validate_message({"value": -3.5e38})

        assert result.is_valid is False
        assert any("float32 range" in err for err in result.errors)

    def test_float32_above_max_invalid(self):
        """Test that values above float32 max are invalid."""
        validator = OscValidator()

        result = validator.validate_message({"value": 3.5e38})

        assert result.is_valid is False
        assert any("float32 range" in err for err in result.errors)

    def test_string_values_valid(self):
        """Test that string values are valid."""
        validator = OscValidator()

        result = validator.validate_message({
            "empty": "",
            "simple": "hello",
            "unicode": "Hello 世界 🎵",
            "long": "a" * 1000,
        })

        assert result.is_valid is True

    def test_bytes_values_valid(self):
        """Test that bytes values are valid."""
        validator = OscValidator()

        result = validator.validate_message({
            "blob": b"binary data",
            "empty_blob": b"",
        })

        assert result.is_valid is True

    def test_bool_values_valid(self):
        """Test that boolean values are accepted."""
        validator = OscValidator()

        result = validator.validate_message({
            "true": True,
            "false": False,
        })

        assert result.is_valid is True

    def test_list_values_invalid(self):
        """Test that list values are invalid."""
        validator = OscValidator()

        result = validator.validate_message({"array": [1, 2, 3]})

        assert result.is_valid is False
        assert any("list" in err.lower() for err in result.errors)

    def test_dict_values_invalid(self):
        """Test that dict values are invalid."""
        validator = OscValidator()

        result = validator.validate_message({"nested": {"key": "value"}})

        assert result.is_valid is False
        assert any("dict" in err.lower() for err in result.errors)

    def test_none_values_invalid(self):
        """Test that None values are invalid."""
        validator = OscValidator()

        result = validator.validate_message({"null": None})

        assert result.is_valid is False
        assert any("none" in err.lower() for err in result.errors)


class TestOscErrorAccumulation:
    """Test that multiple errors are accumulated."""

    def test_multiple_errors_accumulated(self):
        """Test that multiple errors are all reported."""
        validator = OscValidator()

        result = validator.validate_message({
            "bad key": "value",  # Space in key
            "int_overflow": 2147483648,  # Int32 overflow
            "list_val": [1, 2, 3],  # Invalid type
        })

        assert result.is_valid is False
        assert len(result.errors) >= 3  # At least one error per violation


class TestMidiValidatorBasics:
    """Test basic MIDI validation functionality."""

    def test_empty_params_invalid(self):
        """Test that empty params are invalid for MIDI."""
        validator = MidiValidator()

        result = validator.validate_message({})

        assert result.is_valid is False
        assert any("empty" in err.lower() for err in result.errors)

    def test_valid_note_message(self):
        """Test validation of valid note message."""
        validator = MidiValidator()

        result = validator.validate_message({"note": 60, "velocity": 100})

        assert result.is_valid is True
        assert result.errors == []

    def test_valid_cc_message(self):
        """Test validation of valid CC message."""
        validator = MidiValidator()

        result = validator.validate_message({"cc": 7, "value": 127, "channel": 0})

        assert result.is_valid is True


class TestMidiNoteValidation:
    """Test MIDI note number validation."""

    @pytest.mark.parametrize("note", [0, 60, 127])
    def test_valid_note_numbers(self, note):
        """Test that valid note numbers (0-127) are accepted."""
        validator = MidiValidator()

        result = validator.validate_message({"note": note})

        assert result.is_valid is True

    @pytest.mark.parametrize("note", [-1, 128, 255])
    def test_invalid_note_numbers(self, note):
        """Test that invalid note numbers are rejected."""
        validator = MidiValidator()

        result = validator.validate_message({"note": note})

        assert result.is_valid is False
        assert any("note" in err.lower() for err in result.errors)

    def test_note_non_int_invalid(self):
        """Test that non-integer note is invalid."""
        validator = MidiValidator()

        result = validator.validate_message({"note": 60.5})

        assert result.is_valid is False
        assert any("must be int" in err for err in result.errors)


class TestMidiVelocityValidation:
    """Test MIDI velocity validation."""

    @pytest.mark.parametrize("velocity", [0, 64, 127])
    def test_valid_velocity_values(self, velocity):
        """Test that valid velocity values (0-127) are accepted."""
        validator = MidiValidator()

        result = validator.validate_message({"velocity": velocity})

        assert result.is_valid is True

    @pytest.mark.parametrize("velocity", [-1, 128, 255])
    def test_invalid_velocity_values(self, velocity):
        """Test that invalid velocity values are rejected."""
        validator = MidiValidator()

        result = validator.validate_message({"velocity": velocity})

        assert result.is_valid is False
        assert any("velocity" in err.lower() for err in result.errors)


class TestMidiChannelValidation:
    """Test MIDI channel validation."""

    @pytest.mark.parametrize("channel", [0, 7, 15])
    def test_valid_0_to_15_channels(self, channel):
        """Test that 0-15 channel range is valid."""
        validator = MidiValidator()

        result = validator.validate_message({"channel": channel})

        assert result.is_valid is True

    @pytest.mark.parametrize("channel", [1, 8, 16])
    def test_valid_1_to_16_channels(self, channel):
        """Test that 1-16 channel range is also valid."""
        validator = MidiValidator()

        result = validator.validate_message({"channel": channel})

        assert result.is_valid is True

    @pytest.mark.parametrize("channel", [-1, 17, 255])
    def test_invalid_channels(self, channel):
        """Test that channels outside 0-15/1-16 are invalid."""
        validator = MidiValidator()

        result = validator.validate_message({"channel": channel})

        assert result.is_valid is False
        assert any("channel" in err.lower() for err in result.errors)

    def test_channel_non_int_invalid(self):
        """Test that non-integer channel is invalid."""
        validator = MidiValidator()

        result = validator.validate_message({"channel": "1"})

        assert result.is_valid is False
        assert any("must be int" in err for err in result.errors)


class TestMidiCCValidation:
    """Test MIDI CC validation."""

    @pytest.mark.parametrize("cc", [0, 64, 127])
    def test_valid_cc_numbers(self, cc):
        """Test that valid CC numbers (0-127) are accepted."""
        validator = MidiValidator()

        result = validator.validate_message({"cc": cc})

        assert result.is_valid is True

    @pytest.mark.parametrize("cc", [-1, 128, 255])
    def test_invalid_cc_numbers(self, cc):
        """Test that invalid CC numbers are rejected."""
        validator = MidiValidator()

        result = validator.validate_message({"cc": cc})

        assert result.is_valid is False
        assert any("cc" in err.lower() for err in result.errors)

    @pytest.mark.parametrize("value", [0, 64, 127])
    def test_valid_cc_values(self, value):
        """Test that valid CC values (0-127) are accepted."""
        validator = MidiValidator()

        result = validator.validate_message({"cc": 7, "value": value})

        assert result.is_valid is True

    @pytest.mark.parametrize("value", [-1, 128, 255])
    def test_invalid_cc_values(self, value):
        """Test that invalid CC values are rejected."""
        validator = MidiValidator()

        result = validator.validate_message({"cc": 7, "value": value})

        assert result.is_valid is False
        assert any("value" in err.lower() for err in result.errors)


class TestMidiProgramValidation:
    """Test MIDI program change validation."""

    @pytest.mark.parametrize("program", [0, 64, 127])
    def test_valid_program_numbers(self, program):
        """Test that valid program numbers (0-127) are accepted."""
        validator = MidiValidator()

        result = validator.validate_message({"program": program})

        assert result.is_valid is True

    @pytest.mark.parametrize("program", [-1, 128, 255])
    def test_invalid_program_numbers(self, program):
        """Test that invalid program numbers are rejected."""
        validator = MidiValidator()

        result = validator.validate_message({"program": program})

        assert result.is_valid is False
        assert any("program" in err.lower() for err in result.errors)


class TestMidiPitchBendValidation:
    """Test MIDI pitch bend validation."""

    @pytest.mark.parametrize("pitch_bend", [0, 8192, 16383])
    def test_valid_pitch_bend_values(self, pitch_bend):
        """Test that valid pitch bend values (0-16383) are accepted."""
        validator = MidiValidator()

        result = validator.validate_message({"pitch_bend": pitch_bend})

        assert result.is_valid is True

    @pytest.mark.parametrize("pitch_bend", [-1, 16384, 20000])
    def test_invalid_pitch_bend_values(self, pitch_bend):
        """Test that invalid pitch bend values are rejected."""
        validator = MidiValidator()

        result = validator.validate_message({"pitch_bend": pitch_bend})

        assert result.is_valid is False
        assert any("pitch_bend" in err.lower() for err in result.errors)


class TestMidiDurationValidation:
    """Test MIDI duration validation."""

    @pytest.mark.parametrize("duration", [0, 100, 1000.5])
    def test_valid_durations(self, duration):
        """Test that non-negative durations are valid."""
        validator = MidiValidator()

        result = validator.validate_message({"duration_ms": duration})

        assert result.is_valid is True

    def test_negative_duration_invalid(self):
        """Test that negative duration is invalid."""
        validator = MidiValidator()

        result = validator.validate_message({"duration_ms": -10})

        assert result.is_valid is False
        assert any("non-negative" in err.lower() for err in result.errors)

    def test_duration_non_numeric_invalid(self):
        """Test that non-numeric duration is invalid."""
        validator = MidiValidator()

        result = validator.validate_message({"duration_ms": "100"})

        assert result.is_valid is False
        assert any("numeric" in err.lower() for err in result.errors)


class TestMidiErrorAccumulation:
    """Test that multiple MIDI errors are accumulated."""

    def test_multiple_errors_accumulated(self):
        """Test that multiple errors are all reported."""
        validator = MidiValidator()

        result = validator.validate_message({
            "note": 128,  # Out of range
            "velocity": -1,  # Out of range
            "channel": 17,  # Out of range
        })

        assert result.is_valid is False
        assert len(result.errors) >= 3  # At least one error per violation
