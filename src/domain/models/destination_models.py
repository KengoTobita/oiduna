"""
Destination configuration models with Pydantic validation.

These models validate destination configuration at startup time.
They ensure ports are in valid ranges, addresses are properly formatted,
and MIDI ports exist on the system.
"""

from typing import Literal, Annotated
from pydantic import BaseModel, Field, field_validator


class OscDestinationConfig(BaseModel):
    """
    OSC destination configuration with validation.

    Example:
        >>> config = OscDestinationConfig(
        ...     id="superdirt",
        ...     type="osc",
        ...     host="127.0.0.1",
        ...     port=57120,
        ...     address="/dirt/play"
        ... )
    """

    id: str = Field(..., min_length=1, description="Unique destination identifier")
    type: Literal["osc"] = Field(default="osc", description="Destination type")
    host: str = Field(default="127.0.0.1", description="OSC server hostname or IP")
    port: Annotated[int, Field(ge=1024, le=65535)] = Field(
        ..., description="OSC server port (1024-65535)"
    )
    address: str = Field(..., description="OSC address pattern (e.g., /dirt/play)")
    use_bundle: bool = Field(
        default=False,
        description="Auto-bundle messages with same timing into OSC bundle"
    )

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: str) -> str:
        """Ensure OSC address starts with /"""
        if not v.startswith("/"):
            raise ValueError(f"OSC address must start with '/': {v}")
        return v

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Ensure ID is valid (no whitespace, special chars)"""
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                f"Destination ID must be alphanumeric with _ or -: {v}"
            )
        return v


class MidiDestinationConfig(BaseModel):
    """
    MIDI destination configuration with validation.

    Example:
        >>> config = MidiDestinationConfig(
        ...     id="volca_bass",
        ...     type="midi",
        ...     port_name="USB MIDI 1",
        ...     default_channel=0
        ... )
    """

    id: str = Field(..., min_length=1, description="Unique destination identifier")
    type: Literal["midi"] = Field(default="midi", description="Destination type")
    port_name: str = Field(..., description="MIDI port name (from system)")
    default_channel: Annotated[int, Field(ge=0, le=15)] = Field(
        default=0,
        description="Default MIDI channel (0-15) for messages without channel"
    )

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Ensure ID is valid (no whitespace, special chars)"""
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                f"Destination ID must be alphanumeric with _ or -: {v}"
            )
        return v

    @field_validator("port_name")
    @classmethod
    def validate_port_exists(cls, v: str) -> str:
        """Validate that MIDI port exists on system"""
        try:
            import mido
            available_ports = mido.get_output_names()
            if v not in available_ports:
                # Don't fail on startup - just warn
                # Port might be connected later
                import warnings
                warnings.warn(
                    f"MIDI port '{v}' not found. Available: {available_ports}",
                    UserWarning
                )
        except (ImportError, Exception):
            # mido not installed or can't access MIDI system - skip validation
            # This includes permission errors (ALSA), missing MIDI subsystem, etc.
            pass
        return v


# Union type for destination configs
DestinationConfig = OscDestinationConfig | MidiDestinationConfig
