"""Tests for destination parameter type definitions."""

import pytest
from oiduna.domain.models.params import SuperDirtParams, SimpleMidiParams, DestinationParams


class TestSuperDirtParams:
    """Test SuperDirt parameter TypedDict."""

    def test_basic_sound_params(self):
        """Test basic sound parameters."""
        params: SuperDirtParams = {
            "s": "bd",
            "gain": 0.8,
            "pan": 0.5,
        }
        assert params["s"] == "bd"
        assert params["gain"] == 0.8
        assert params["pan"] == 0.5

    def test_effect_params(self):
        """Test effect parameters."""
        params: SuperDirtParams = {
            "room": 0.3,
            "size": 0.8,
            "delay_send": 0.2,
            "cutoff": 1000,
            "resonance": 0.3,
        }
        assert params["room"] == 0.3
        assert params["cutoff"] == 1000

    def test_orbit_param(self):
        """Test orbit parameter."""
        params: SuperDirtParams = {"orbit": 2}
        assert params["orbit"] == 2

    def test_empty_params(self):
        """Test empty parameters (all fields optional)."""
        params: SuperDirtParams = {}
        assert len(params) == 0

    def test_mixed_params(self):
        """Test mixed parameter combination."""
        params: SuperDirtParams = {
            "s": "hh",
            "n": 3,
            "gain": 0.6,
            "pan": 0.7,
            "speed": 1.2,
            "room": 0.1,
            "delay_send": 0.15,
        }
        assert params["s"] == "hh"
        assert params["n"] == 3
        assert params["speed"] == 1.2

    def test_dict_compatibility(self):
        """Test that SuperDirtParams is dict-compatible."""
        params: SuperDirtParams = {"s": "bd", "gain": 0.8}
        # Should work with dict operations
        assert "s" in params
        assert len(params) == 2
        params["pan"] = 0.5
        assert params["pan"] == 0.5


class TestSimpleMidiParams:
    """Test SimpleMIDI parameter TypedDict."""

    def test_note_on_params(self):
        """Test Note On parameters."""
        params: SimpleMidiParams = {
            "note": 60,
            "velocity": 100,
            "duration_ms": 250,
            "channel": 0,
        }
        assert params["note"] == 60
        assert params["velocity"] == 100
        assert params["duration_ms"] == 250
        assert params["channel"] == 0

    def test_control_change_params(self):
        """Test Control Change parameters."""
        params: SimpleMidiParams = {
            "cc": 74,
            "value": 64,
            "channel": 0,
        }
        assert params["cc"] == 74
        assert params["value"] == 64

    def test_pitch_bend_params(self):
        """Test Pitch Bend parameters."""
        params: SimpleMidiParams = {
            "pitch_bend": 2048,
            "channel": 0,
        }
        assert params["pitch_bend"] == 2048

    def test_program_change_params(self):
        """Test Program Change parameters."""
        params: SimpleMidiParams = {
            "program": 42,
            "channel": 1,
        }
        assert params["program"] == 42

    def test_empty_params(self):
        """Test empty parameters (all fields optional)."""
        params: SimpleMidiParams = {}
        assert len(params) == 0

    def test_dict_compatibility(self):
        """Test that SimpleMidiParams is dict-compatible."""
        params: SimpleMidiParams = {"note": 60, "velocity": 100}
        # Should work with dict operations
        assert "note" in params
        assert len(params) == 2
        params["channel"] = 0
        assert params["channel"] == 0


class TestDestinationParams:
    """Test DestinationParams union type."""

    def test_superdirt_params_as_destination_params(self):
        """Test SuperDirtParams can be used as DestinationParams."""
        params: DestinationParams = {"s": "bd", "gain": 0.8}
        assert isinstance(params, dict)

    def test_midi_params_as_destination_params(self):
        """Test SimpleMidiParams can be used as DestinationParams."""
        params: DestinationParams = {"note": 60, "velocity": 100}
        assert isinstance(params, dict)

    def test_custom_params_as_destination_params(self):
        """Test custom dict can be used as DestinationParams."""
        params: DestinationParams = {
            "custom_param_1": "value",
            "custom_param_2": 123,
            "custom_param_3": [1, 2, 3],
        }
        assert params["custom_param_1"] == "value"
        assert params["custom_param_2"] == 123


class TestParameterCombinations:
    """Test realistic parameter combinations."""

    def test_superdirt_kick_pattern(self):
        """Test typical kick drum pattern parameters."""
        kick: SuperDirtParams = {
            "s": "bd",
            "n": 0,
            "gain": 0.9,
            "pan": 0.5,
            "room": 0.1,
            "orbit": 0,
        }
        assert kick["s"] == "bd"
        assert kick["orbit"] == 0

    def test_superdirt_hihat_pattern(self):
        """Test typical hi-hat pattern parameters."""
        hihat: SuperDirtParams = {
            "s": "hh",
            "n": 2,
            "gain": 0.6,
            "pan": 0.7,
            "cutoff": 8000,
            "speed": 1.5,
        }
        assert hihat["s"] == "hh"
        assert hihat["cutoff"] == 8000

    def test_midi_bass_note(self):
        """Test typical MIDI bass note."""
        bass_note: MidiParams = {
            "note": 36,  # C1
            "velocity": 90,
            "duration_ms": 500,
            "channel": 1,
        }
        assert bass_note["note"] == 36
        assert bass_note["channel"] == 1

    def test_midi_cc_filter_sweep(self):
        """Test MIDI CC for filter sweep."""
        filter_cc: MidiParams = {
            "cc": 74,  # Filter cutoff
            "value": 127,
            "channel": 0,
        }
        assert filter_cc["cc"] == 74


class TestTypeAnnotations:
    """Test type annotation examples (documentation)."""

    def test_function_parameter_annotation(self):
        """Test using params types in function signatures."""

        def create_kick(params: SuperDirtParams) -> dict:
            """Example function accepting SuperDirtParams."""
            return dict(params)

        result = create_kick({"s": "bd", "gain": 0.8})
        assert result["s"] == "bd"

    def test_variable_annotation(self):
        """Test variable type annotations."""
        # These annotations help with editor autocomplete
        kick_params: SuperDirtParams = {"s": "bd"}
        midi_params: SimpleMidiParams = {"note": 60}
        custom_params: DestinationParams = {"custom": "value"}

        assert kick_params["s"] == "bd"
        assert midi_params["note"] == 60
        assert custom_params["custom"] == "value"
