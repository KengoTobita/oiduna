"""
Tests for OSC protocol validator.
"""

import sys
from pathlib import Path

# Add packages directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "packages" / "oiduna_scheduler"))

import pytest
from validators.osc_validator import OscValidator, OscValidationResult


class TestOscValidator:
    """Test OSC message validation."""

    def test_empty_params_valid(self):
        """Empty params dict is valid (rare but allowed)."""
        validator = OscValidator()
        result = validator.validate_message({})
        assert result.is_valid
        assert len(result.errors) == 0

    def test_valid_superdirt_message(self):
        """SuperDirt-style message should validate."""
        validator = OscValidator()
        params = {
            "s": "bd",
            "orbit": 0,
            "gain": 0.8,
            "pan": 0.5,
            "delaySend": 0.2,
            "room": 0.3,
        }
        result = validator.validate_message(params)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_valid_int_param(self):
        """Integer params should validate."""
        validator = OscValidator()
        result = validator.validate_message({"orbit": 0, "note": 60})
        assert result.is_valid

    def test_valid_float_param(self):
        """Float params should validate."""
        validator = OscValidator()
        result = validator.validate_message({"gain": 0.8, "pan": 0.5})
        assert result.is_valid

    def test_valid_string_param(self):
        """String params should validate."""
        validator = OscValidator()
        result = validator.validate_message({"s": "bd", "vowel": "a"})
        assert result.is_valid

    def test_valid_bytes_param(self):
        """Bytes params should validate."""
        validator = OscValidator()
        result = validator.validate_message({"data": b"test"})
        assert result.is_valid

    def test_valid_bool_param(self):
        """Bool params are allowed (convert to int)."""
        validator = OscValidator()
        result = validator.validate_message({"mute": True, "solo": False})
        assert result.is_valid

    def test_int32_overflow(self):
        """Integer exceeding int32 range should fail."""
        validator = OscValidator()
        result = validator.validate_message({"big": 2**31})  # Exceeds int32 max
        assert not result.is_valid
        assert any("int32 range" in err for err in result.errors)

    def test_int32_underflow(self):
        """Integer below int32 range should fail."""
        validator = OscValidator()
        result = validator.validate_message({"small": -(2**31) - 1})
        assert not result.is_valid
        assert any("int32 range" in err for err in result.errors)

    def test_float32_overflow(self):
        """Float exceeding float32 range should fail."""
        validator = OscValidator()
        result = validator.validate_message({"huge": 1e39})
        assert not result.is_valid
        assert any("float32 range" in err for err in result.errors)

    def test_list_param_rejected(self):
        """List params should be rejected (not in OSC 1.0)."""
        validator = OscValidator()
        result = validator.validate_message({"notes": [60, 64, 67]})
        assert not result.is_valid
        assert any("list value" in err for err in result.errors)

    def test_dict_param_rejected(self):
        """Dict params should be rejected."""
        validator = OscValidator()
        result = validator.validate_message({"nested": {"key": "value"}})
        assert not result.is_valid
        assert any("dict value" in err for err in result.errors)

    def test_none_param_rejected(self):
        """None params should be rejected."""
        validator = OscValidator()
        result = validator.validate_message({"empty": None})
        assert not result.is_valid
        assert any("None value" in err for err in result.errors)

    def test_empty_key_rejected(self):
        """Empty string key should be rejected."""
        validator = OscValidator()
        result = validator.validate_message({"": "value"})
        assert not result.is_valid
        assert any("cannot be empty" in err for err in result.errors)

    def test_key_with_space_rejected(self):
        """Key with space should be rejected."""
        validator = OscValidator()
        result = validator.validate_message({"bad key": "value"})
        assert not result.is_valid
        assert any("forbidden character" in err for err in result.errors)

    def test_key_with_forbidden_chars_rejected(self):
        """Keys with OSC forbidden characters should be rejected."""
        validator = OscValidator()
        forbidden = ["#", "*", ",", "?", "[", "]", "{", "}"]
        for char in forbidden:
            result = validator.validate_message({f"bad{char}key": "value"})
            assert not result.is_valid
            assert any("forbidden character" in err for err in result.errors)

    def test_multiple_errors(self):
        """Message with multiple errors should report all."""
        validator = OscValidator()
        result = validator.validate_message({
            "bad key": "value",  # Space in key
            "overflow": 2**31,  # Int overflow
            "list": [1, 2, 3],  # List not supported
        })
        assert not result.is_valid
        assert len(result.errors) >= 3  # At least 3 errors

    def test_validation_result_success(self):
        """Test OscValidationResult.success() factory."""
        result = OscValidationResult.success()
        assert result.is_valid
        assert result.errors == []

    def test_validation_result_failure(self):
        """Test OscValidationResult.failure() factory."""
        errors = ["error 1", "error 2"]
        result = OscValidationResult.failure(errors)
        assert not result.is_valid
        assert result.errors == errors

    def test_camelcase_keys_valid(self):
        """SuperDirt uses camelCase keys - should be valid."""
        validator = OscValidator()
        result = validator.validate_message({
            "delaySend": 0.2,
            "delayTime": 0.5,
            "roomSize": 0.8,
        })
        assert result.is_valid

    def test_mixed_types_valid(self):
        """Message with mixed valid types should validate."""
        validator = OscValidator()
        result = validator.validate_message({
            "s": "bd",  # string
            "orbit": 0,  # int
            "gain": 0.8,  # float
            "mute": False,  # bool
        })
        assert result.is_valid
