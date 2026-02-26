"""Tests for destination configuration loader."""

import pytest
import tempfile
from pathlib import Path

from loader import load_destinations, load_destinations_from_file
from destination_models import OscDestinationConfig, MidiDestinationConfig


class TestLoadDestinations:
    """Tests for load_destinations function."""

    def test_load_single_osc_destination(self):
        """Test loading single OSC destination."""
        config_data = {
            "destinations": {
                "superdirt": {
                    "id": "superdirt",
                    "type": "osc",
                    "host": "127.0.0.1",
                    "port": 57120,
                    "address": "/dirt/play"
                }
            }
        }

        destinations = load_destinations(config_data)

        assert len(destinations) == 1
        assert "superdirt" in destinations
        assert isinstance(destinations["superdirt"], OscDestinationConfig)
        assert destinations["superdirt"].port == 57120

    def test_load_single_midi_destination(self):
        """Test loading single MIDI destination."""
        config_data = {
            "destinations": {
                "volca": {
                    "id": "volca",
                    "type": "midi",
                    "port_name": "USB MIDI 1",
                    "default_channel": 0
                }
            }
        }

        # Don't check for warning - MIDI access may not be available in test environment
        destinations = load_destinations(config_data)

        assert len(destinations) == 1
        assert "volca" in destinations
        assert isinstance(destinations["volca"], MidiDestinationConfig)

    def test_load_multiple_destinations(self):
        """Test loading multiple destinations."""
        config_data = {
            "destinations": {
                "superdirt": {
                    "id": "superdirt",
                    "type": "osc",
                    "port": 57120,
                    "address": "/dirt/play"
                },
                "volca": {
                    "id": "volca",
                    "type": "midi",
                    "port_name": "USB MIDI 1"
                }
            }
        }

        # Don't check for warning - MIDI access may not be available in test environment
        destinations = load_destinations(config_data)

        assert len(destinations) == 2
        assert "superdirt" in destinations
        assert "volca" in destinations

    def test_auto_fill_id_from_key(self):
        """Test that ID is auto-filled from dictionary key."""
        config_data = {
            "destinations": {
                "superdirt": {
                    "type": "osc",
                    "port": 57120,
                    "address": "/dirt/play"
                }
            }
        }

        destinations = load_destinations(config_data)
        assert destinations["superdirt"].id == "superdirt"

    def test_id_mismatch_raises_error(self):
        """Test that ID mismatch raises error."""
        config_data = {
            "destinations": {
                "superdirt": {
                    "id": "different_id",  # Doesn't match key
                    "type": "osc",
                    "port": 57120,
                    "address": "/dirt/play"
                }
            }
        }

        with pytest.raises(ValueError, match="ID mismatch"):
            load_destinations(config_data)

    def test_missing_destinations_key(self):
        """Test error when 'destinations' key is missing."""
        config_data = {"other_key": {}}

        with pytest.raises(ValueError, match="must have 'destinations' key"):
            load_destinations(config_data)

    def test_destinations_not_dict(self):
        """Test error when 'destinations' is not a dictionary."""
        config_data = {"destinations": []}

        with pytest.raises(ValueError, match="must be a dictionary"):
            load_destinations(config_data)

    def test_unknown_destination_type(self):
        """Test error for unknown destination type."""
        config_data = {
            "destinations": {
                "unknown": {
                    "id": "unknown",
                    "type": "websocket",  # Not supported
                    "url": "ws://localhost"
                }
            }
        }

        with pytest.raises(ValueError, match="Unknown destination type"):
            load_destinations(config_data)


class TestLoadDestinationsFromFile:
    """Tests for load_destinations_from_file function."""

    def test_load_yaml_file(self):
        """Test loading from YAML file."""
        yaml_content = """
destinations:
  superdirt:
    id: superdirt
    type: osc
    host: 127.0.0.1
    port: 57120
    address: /dirt/play
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            destinations = load_destinations_from_file(temp_path)
            assert len(destinations) == 1
            assert "superdirt" in destinations
        finally:
            Path(temp_path).unlink()

    def test_load_yml_extension(self):
        """Test loading from .yml file."""
        yaml_content = """
destinations:
  test:
    type: osc
    port: 57120
    address: /test
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            destinations = load_destinations_from_file(temp_path)
            assert "test" in destinations
        finally:
            Path(temp_path).unlink()

    def test_load_json_file(self):
        """Test loading from JSON file."""
        json_content = """
{
  "destinations": {
    "superdirt": {
      "id": "superdirt",
      "type": "osc",
      "port": 57120,
      "address": "/dirt/play"
    }
  }
}
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(json_content)
            temp_path = f.name

        try:
            destinations = load_destinations_from_file(temp_path)
            assert len(destinations) == 1
            assert "superdirt" in destinations
        finally:
            Path(temp_path).unlink()

    def test_file_not_found(self):
        """Test error when file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            load_destinations_from_file("/nonexistent/path.yaml")

    def test_invalid_yaml_syntax(self):
        """Test error for invalid YAML syntax."""
        invalid_yaml = """
destinations:
  test:
    - invalid
    - yaml
    syntax
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(invalid_yaml)
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="Invalid YAML"):
                load_destinations_from_file(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_invalid_json_syntax(self):
        """Test error for invalid JSON syntax."""
        invalid_json = """
{
  "destinations": {
    "test": {
      "type": "osc"
      missing comma
    }
  }
}
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(invalid_json)
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="Invalid JSON"):
                load_destinations_from_file(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_unsupported_file_format(self):
        """Test error for unsupported file format."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("test")
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="Unsupported file format"):
                load_destinations_from_file(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_file_not_dict(self):
        """Test error when file contains non-dict data."""
        yaml_content = """
- list
- not
- dict
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="must be a dictionary"):
                load_destinations_from_file(temp_path)
        finally:
            Path(temp_path).unlink()
