"""Tests for offset validation."""

import pytest
from oiduna.domain.models.timing import validate_offset


class TestOffsetValidation:
    """Test offset validation function."""

    def test_offset_zero_valid(self):
        """Test that offset 0.0 is valid."""
        assert validate_offset(0.0) == 0.0

    def test_offset_half_valid(self):
        """Test that offset 0.5 is valid."""
        assert validate_offset(0.5) == 0.5

    def test_offset_near_one_valid(self):
        """Test that offset near 1.0 is valid."""
        assert validate_offset(0.999) == 0.999
        assert validate_offset(0.9999) == 0.9999

    def test_offset_one_invalid(self):
        """Test that offset 1.0 is invalid (half-open interval)."""
        with pytest.raises(ValueError, match="Offset must be in range"):
            validate_offset(1.0)

    def test_offset_above_one_invalid(self):
        """Test that offset > 1.0 is invalid."""
        with pytest.raises(ValueError, match="Offset must be in range"):
            validate_offset(1.1)
        with pytest.raises(ValueError, match="Offset must be in range"):
            validate_offset(2.0)

    def test_offset_negative_invalid(self):
        """Test that negative offset is invalid."""
        with pytest.raises(ValueError, match="Offset must be in range"):
            validate_offset(-0.1)
        with pytest.raises(ValueError, match="Offset must be in range"):
            validate_offset(-1.0)

    def test_offset_common_swing_values(self):
        """Test common swing offset values."""
        # Swing 16ths (2:1 ratio)
        assert validate_offset(0.666) == 0.666
        assert validate_offset(0.6666666666666666) == 0.6666666666666666

        # Triplet divisions
        assert validate_offset(0.333) == 0.333
        assert validate_offset(0.3333333333333333) == 0.3333333333333333
