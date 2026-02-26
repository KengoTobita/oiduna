"""
Tests for MIDI protocol validator.
"""

import sys
from pathlib import Path

# Add packages directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "packages" / "oiduna_scheduler"))

import pytest
from validators.midi_validator import MidiValidator, MidiValidationResult


class TestMidiValidator:
    """Test MIDI message validation."""

    def test_empty_params_rejected(self):
        """Empty params dict should be rejected for MIDI."""
        validator = MidiValidator()
        result = validator.validate_message({})
        assert not result.is_valid
        assert any("cannot have empty params" in err for err in result.errors)

    def test_valid_note_on_message(self):
        """Standard note-on message should validate."""
        validator = MidiValidator()
        params = {
            "channel": 0,
            "note": 60,
            "velocity": 100,
        }
        result = validator.validate_message(params)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_valid_note_with_duration(self):
        """Note message with duration should validate."""
        validator = MidiValidator()
        params = {
            "channel": 0,
            "note": 60,
            "velocity": 100,
            "duration_ms": 250,
        }
        result = validator.validate_message(params)
        assert result.is_valid

    def test_valid_cc_message(self):
        """Control Change message should validate."""
        validator = MidiValidator()
        params = {
            "channel": 0,
            "cc": 7,  # Volume
            "value": 100,
        }
        result = validator.validate_message(params)
        assert result.is_valid

    def test_valid_program_change(self):
        """Program change message should validate."""
        validator = MidiValidator()
        params = {
            "channel": 0,
            "program": 5,
        }
        result = validator.validate_message(params)
        assert result.is_valid

    def test_valid_pitch_bend(self):
        """Pitch bend message should validate."""
        validator = MidiValidator()
        params = {
            "channel": 0,
            "pitch_bend": 8192,  # Center
        }
        result = validator.validate_message(params)
        assert result.is_valid

    def test_note_min_boundary(self):
        """Note 0 (lowest MIDI note) should validate."""
        validator = MidiValidator()
        result = validator.validate_message({"note": 0})
        assert result.is_valid

    def test_note_max_boundary(self):
        """Note 127 (highest MIDI note) should validate."""
        validator = MidiValidator()
        result = validator.validate_message({"note": 127})
        assert result.is_valid

    def test_note_below_range(self):
        """Note < 0 should fail."""
        validator = MidiValidator()
        result = validator.validate_message({"note": -1})
        assert not result.is_valid
        assert any("note" in err and "0-127" in err for err in result.errors)

    def test_note_above_range(self):
        """Note > 127 should fail."""
        validator = MidiValidator()
        result = validator.validate_message({"note": 128})
        assert not result.is_valid
        assert any("note" in err and "0-127" in err for err in result.errors)

    def test_velocity_min_boundary(self):
        """Velocity 0 (note off) should validate."""
        validator = MidiValidator()
        result = validator.validate_message({"velocity": 0})
        assert result.is_valid

    def test_velocity_max_boundary(self):
        """Velocity 127 (max) should validate."""
        validator = MidiValidator()
        result = validator.validate_message({"velocity": 127})
        assert result.is_valid

    def test_velocity_below_range(self):
        """Velocity < 0 should fail."""
        validator = MidiValidator()
        result = validator.validate_message({"velocity": -1})
        assert not result.is_valid
        assert any("velocity" in err and "0-127" in err for err in result.errors)

    def test_velocity_above_range(self):
        """Velocity > 127 should fail."""
        validator = MidiValidator()
        result = validator.validate_message({"velocity": 128})
        assert not result.is_valid
        assert any("velocity" in err and "0-127" in err for err in result.errors)

    def test_channel_0_to_15_valid(self):
        """Channels 0-15 should validate."""
        validator = MidiValidator()
        for channel in range(16):
            result = validator.validate_message({"channel": channel})
            assert result.is_valid, f"Channel {channel} should be valid"

    def test_channel_1_to_16_valid(self):
        """Channels 1-16 should validate (alternative numbering)."""
        validator = MidiValidator()
        for channel in range(1, 17):
            result = validator.validate_message({"channel": channel})
            assert result.is_valid, f"Channel {channel} should be valid"

    def test_channel_below_range(self):
        """Channel < 0 should fail."""
        validator = MidiValidator()
        result = validator.validate_message({"channel": -1})
        assert not result.is_valid
        assert any("channel" in err for err in result.errors)

    def test_channel_above_range(self):
        """Channel > 16 should fail."""
        validator = MidiValidator()
        result = validator.validate_message({"channel": 17})
        assert not result.is_valid
        assert any("channel" in err for err in result.errors)

    def test_cc_number_min_boundary(self):
        """CC 0 should validate."""
        validator = MidiValidator()
        result = validator.validate_message({"cc": 0, "value": 64})
        assert result.is_valid

    def test_cc_number_max_boundary(self):
        """CC 127 should validate."""
        validator = MidiValidator()
        result = validator.validate_message({"cc": 127, "value": 64})
        assert result.is_valid

    def test_cc_number_below_range(self):
        """CC < 0 should fail."""
        validator = MidiValidator()
        result = validator.validate_message({"cc": -1, "value": 64})
        assert not result.is_valid
        assert any("cc" in err and "0-127" in err for err in result.errors)

    def test_cc_number_above_range(self):
        """CC > 127 should fail."""
        validator = MidiValidator()
        result = validator.validate_message({"cc": 128, "value": 64})
        assert not result.is_valid
        assert any("cc" in err and "0-127" in err for err in result.errors)

    def test_cc_value_min_boundary(self):
        """CC value 0 should validate."""
        validator = MidiValidator()
        result = validator.validate_message({"cc": 7, "value": 0})
        assert result.is_valid

    def test_cc_value_max_boundary(self):
        """CC value 127 should validate."""
        validator = MidiValidator()
        result = validator.validate_message({"cc": 7, "value": 127})
        assert result.is_valid

    def test_cc_value_below_range(self):
        """CC value < 0 should fail."""
        validator = MidiValidator()
        result = validator.validate_message({"cc": 7, "value": -1})
        assert not result.is_valid
        assert any("value" in err and "0-127" in err for err in result.errors)

    def test_cc_value_above_range(self):
        """CC value > 127 should fail."""
        validator = MidiValidator()
        result = validator.validate_message({"cc": 7, "value": 128})
        assert not result.is_valid
        assert any("value" in err and "0-127" in err for err in result.errors)

    def test_program_min_boundary(self):
        """Program 0 should validate."""
        validator = MidiValidator()
        result = validator.validate_message({"program": 0})
        assert result.is_valid

    def test_program_max_boundary(self):
        """Program 127 should validate."""
        validator = MidiValidator()
        result = validator.validate_message({"program": 127})
        assert result.is_valid

    def test_program_below_range(self):
        """Program < 0 should fail."""
        validator = MidiValidator()
        result = validator.validate_message({"program": -1})
        assert not result.is_valid
        assert any("program" in err and "0-127" in err for err in result.errors)

    def test_program_above_range(self):
        """Program > 127 should fail."""
        validator = MidiValidator()
        result = validator.validate_message({"program": 128})
        assert not result.is_valid
        assert any("program" in err and "0-127" in err for err in result.errors)

    def test_pitch_bend_min_boundary(self):
        """Pitch bend 0 should validate."""
        validator = MidiValidator()
        result = validator.validate_message({"pitch_bend": 0})
        assert result.is_valid

    def test_pitch_bend_center(self):
        """Pitch bend 8192 (center) should validate."""
        validator = MidiValidator()
        result = validator.validate_message({"pitch_bend": 8192})
        assert result.is_valid

    def test_pitch_bend_max_boundary(self):
        """Pitch bend 16383 should validate."""
        validator = MidiValidator()
        result = validator.validate_message({"pitch_bend": 16383})
        assert result.is_valid

    def test_pitch_bend_below_range(self):
        """Pitch bend < 0 should fail."""
        validator = MidiValidator()
        result = validator.validate_message({"pitch_bend": -1})
        assert not result.is_valid
        assert any("pitch_bend" in err and "0-16383" in err for err in result.errors)

    def test_pitch_bend_above_range(self):
        """Pitch bend > 16383 should fail."""
        validator = MidiValidator()
        result = validator.validate_message({"pitch_bend": 16384})
        assert not result.is_valid
        assert any("pitch_bend" in err and "0-16383" in err for err in result.errors)

    def test_duration_valid_int(self):
        """Duration as int should validate."""
        validator = MidiValidator()
        result = validator.validate_message({"duration_ms": 250})
        assert result.is_valid

    def test_duration_valid_float(self):
        """Duration as float should validate."""
        validator = MidiValidator()
        result = validator.validate_message({"duration_ms": 250.5})
        assert result.is_valid

    def test_duration_zero_valid(self):
        """Duration 0 should validate."""
        validator = MidiValidator()
        result = validator.validate_message({"duration_ms": 0})
        assert result.is_valid

    def test_duration_negative_rejected(self):
        """Negative duration should fail."""
        validator = MidiValidator()
        result = validator.validate_message({"duration_ms": -100})
        assert not result.is_valid
        assert any("duration_ms" in err and "non-negative" in err for err in result.errors)

    def test_duration_non_numeric_rejected(self):
        """Non-numeric duration should fail."""
        validator = MidiValidator()
        result = validator.validate_message({"duration_ms": "250"})
        assert not result.is_valid
        assert any("duration_ms" in err and "numeric" in err for err in result.errors)

    def test_note_non_int_rejected(self):
        """Float note should fail."""
        validator = MidiValidator()
        result = validator.validate_message({"note": 60.5})
        assert not result.is_valid
        assert any("note" in err and "must be int" in err for err in result.errors)

    def test_velocity_non_int_rejected(self):
        """String velocity should fail."""
        validator = MidiValidator()
        result = validator.validate_message({"velocity": "100"})
        assert not result.is_valid
        assert any("velocity" in err and "must be int" in err for err in result.errors)

    def test_multiple_errors(self):
        """Message with multiple errors should report all."""
        validator = MidiValidator()
        result = validator.validate_message({
            "note": 200,  # Out of range
            "velocity": -50,  # Out of range
            "channel": 20,  # Out of range
        })
        assert not result.is_valid
        assert len(result.errors) >= 3  # At least 3 errors

    def test_validation_result_success(self):
        """Test MidiValidationResult.success() factory."""
        result = MidiValidationResult.success()
        assert result.is_valid
        assert result.errors == []

    def test_validation_result_failure(self):
        """Test MidiValidationResult.failure() factory."""
        errors = ["error 1", "error 2"]
        result = MidiValidationResult.failure(errors)
        assert not result.is_valid
        assert result.errors == errors

    def test_unknown_param_ignored(self):
        """Unknown params should be ignored (forward compatibility)."""
        validator = MidiValidator()
        result = validator.validate_message({
            "note": 60,
            "custom_param": "value",  # Unknown param
        })
        assert result.is_valid  # Validation passes, custom param ignored
