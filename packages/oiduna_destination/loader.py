"""
Destination configuration loader.

Loads destination configurations from YAML or JSON files with validation.
"""

from pathlib import Path
from typing import Any
import yaml
import json

from destination_models import DestinationConfig, OscDestinationConfig, MidiDestinationConfig


def load_destinations(config_data: dict[str, Any]) -> dict[str, DestinationConfig]:
    """
    Load and validate destinations from configuration dictionary.

    Args:
        config_data: Dictionary with "destinations" key containing destination configs

    Returns:
        Dictionary mapping destination_id -> DestinationConfig

    Raises:
        ValueError: If configuration is invalid
        pydantic.ValidationError: If validation fails

    Example:
        >>> config = {
        ...     "destinations": {
        ...         "superdirt": {
        ...             "id": "superdirt",
        ...             "type": "osc",
        ...             "host": "127.0.0.1",
        ...             "port": 57120,
        ...             "address": "/dirt/play"
        ...         }
        ...     }
        ... }
        >>> destinations = load_destinations(config)
        >>> assert "superdirt" in destinations
    """
    if "destinations" not in config_data:
        raise ValueError("Configuration must have 'destinations' key")

    destinations_dict = config_data["destinations"]
    if not isinstance(destinations_dict, dict):
        raise ValueError("'destinations' must be a dictionary")

    destinations: dict[str, DestinationConfig] = {}

    for dest_id, dest_config in destinations_dict.items():
        # Ensure id matches key
        if "id" not in dest_config:
            dest_config["id"] = dest_id
        elif dest_config["id"] != dest_id:
            raise ValueError(
                f"Destination ID mismatch: key='{dest_id}' vs config.id='{dest_config['id']}'"
            )

        # Validate and create appropriate config type
        dest_type = dest_config.get("type")
        if dest_type == "osc":
            config = OscDestinationConfig(**dest_config)
        elif dest_type == "midi":
            config = MidiDestinationConfig(**dest_config)
        else:
            raise ValueError(
                f"Unknown destination type '{dest_type}' for '{dest_id}'. "
                f"Must be 'osc' or 'midi'."
            )

        destinations[dest_id] = config

    return destinations


def load_destinations_from_file(file_path: Path | str) -> dict[str, DestinationConfig]:
    """
    Load destinations from YAML or JSON file.

    Args:
        file_path: Path to YAML or JSON configuration file

    Returns:
        Dictionary mapping destination_id -> DestinationConfig

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file format is invalid or configuration is invalid

    Example:
        >>> destinations = load_destinations_from_file("destinations.yaml")
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Destination config file not found: {path}")

    # Read file content
    content = path.read_text(encoding="utf-8")

    # Parse based on extension
    suffix = path.suffix.lower()
    if suffix in (".yaml", ".yml"):
        try:
            config_data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {path}: {e}") from e
    elif suffix == ".json":
        try:
            config_data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {path}: {e}") from e
    else:
        raise ValueError(
            f"Unsupported file format: {suffix}. Use .yaml, .yml, or .json"
        )

    if not isinstance(config_data, dict):
        raise ValueError(f"Configuration must be a dictionary, got {type(config_data)}")

    return load_destinations(config_data)
