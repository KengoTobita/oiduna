"""
MIDI parameter helpers - protocol validation only.

These helpers validate MIDI protocol constraints (0-127 ranges, etc.)
but make no assumptions about musical meaning (note names, CC assignments).

Supports:
- Standard MIDI messages (note, velocity, channel)
- Control Change (CC)
- Non-Registered Parameter Numbers (NRPN)
"""

from typing import TypedDict, Any


class MidiParams(TypedDict, total=False):
    """
    Type hints for MIDI parameters.

    All fields are optional. Values must conform to MIDI protocol:
    - note: 0-127
    - velocity: 0-127
    - channel: 0-15
    - duration_ms: any positive integer (milliseconds)
    - cc: {cc_number: value} where both are 0-127
    - nrpn: {nrpn_number: value} where both are 0-16383 (14-bit)

    Example:
        >>> # Basic MIDI note
        >>> params: MidiParams = {
        ...     "note": 60,
        ...     "velocity": 100,
        ...     "duration_ms": 250,
        ...     "channel": 0
        ... }

        >>> # With CC
        >>> params: MidiParams = {
        ...     "note": 60,
        ...     "cc": {1: 64, 7: 100}
        ... }

        >>> # With NRPN
        >>> params: MidiParams = {
        ...     "note": 60,
        ...     "nrpn": {256: 8192}  # NRPN #256 = value 8192
        ... }
    """
    note: int              # 0-127
    velocity: int          # 0-127
    duration_ms: int       # milliseconds (any positive int)
    channel: int           # 0-15
    cc: dict[int, int]     # {cc_number: value}, both 0-127
    nrpn: dict[int, int]   # {nrpn_number: value}, both 0-16383 (14-bit)


class MidiValidationError(ValueError):
    """Raised when MIDI parameter is out of protocol range."""
    pass


def validate_midi_params(params: dict[str, Any]) -> None:
    """
    Validate MIDI parameters conform to MIDI protocol.

    Checks:
    - note: 0-127
    - velocity: 0-127
    - channel: 0-15
    - cc keys/values: 0-127
    - nrpn keys/values: 0-16383 (14-bit)

    Args:
        params: Parameter dictionary to validate

    Raises:
        MidiValidationError: If any parameter is out of protocol range

    Example:
        >>> params = {"note": 60, "velocity": 100}
        >>> validate_midi_params(params)  # OK

        >>> params = {"note": 200}
        >>> validate_midi_params(params)
        Traceback (most recent call last):
        ...
        MidiValidationError: MIDI note must be 0-127, got 200

        >>> params = {"nrpn": {256: 8192}}
        >>> validate_midi_params(params)  # OK (14-bit range)
    """
    if "note" in params:
        note = params["note"]
        if not isinstance(note, int) or not (0 <= note <= 127):
            raise MidiValidationError(
                f"MIDI note must be 0-127, got {note}"
            )

    if "velocity" in params:
        velocity = params["velocity"]
        if not isinstance(velocity, int) or not (0 <= velocity <= 127):
            raise MidiValidationError(
                f"MIDI velocity must be 0-127, got {velocity}"
            )

    if "channel" in params:
        channel = params["channel"]
        if not isinstance(channel, int) or not (0 <= channel <= 15):
            raise MidiValidationError(
                f"MIDI channel must be 0-15, got {channel}"
            )

    if "duration_ms" in params:
        duration_ms = params["duration_ms"]
        if not isinstance(duration_ms, int) or duration_ms <= 0:
            raise MidiValidationError(
                f"MIDI duration_ms must be positive integer, got {duration_ms}"
            )

    if "cc" in params:
        cc = params["cc"]
        if not isinstance(cc, dict):
            raise MidiValidationError(
                f"MIDI cc must be dict, got {type(cc).__name__}"
            )
        for cc_num, cc_val in cc.items():
            if not isinstance(cc_num, int) or not (0 <= cc_num <= 127):
                raise MidiValidationError(
                    f"MIDI CC number must be 0-127, got {cc_num}"
                )
            if not isinstance(cc_val, int) or not (0 <= cc_val <= 127):
                raise MidiValidationError(
                    f"MIDI CC value must be 0-127, got {cc_val}"
                )

    if "nrpn" in params:
        nrpn = params["nrpn"]
        if not isinstance(nrpn, dict):
            raise MidiValidationError(
                f"MIDI nrpn must be dict, got {type(nrpn).__name__}"
            )
        for nrpn_num, nrpn_val in nrpn.items():
            if not isinstance(nrpn_num, int) or not (0 <= nrpn_num <= 16383):
                raise MidiValidationError(
                    f"MIDI NRPN number must be 0-16383 (14-bit), got {nrpn_num}"
                )
            if not isinstance(nrpn_val, int) or not (0 <= nrpn_val <= 16383):
                raise MidiValidationError(
                    f"MIDI NRPN value must be 0-16383 (14-bit), got {nrpn_val}"
                )


def is_valid_midi_params(params: dict[str, Any]) -> bool:
    """
    Check if MIDI parameters are valid (non-raising version).

    Args:
        params: Parameter dictionary to validate

    Returns:
        True if valid, False otherwise

    Example:
        >>> is_valid_midi_params({"note": 60})
        True
        >>> is_valid_midi_params({"note": 200})
        False
        >>> is_valid_midi_params({"nrpn": {256: 8192}})
        True
    """
    try:
        validate_midi_params(params)
        return True
    except MidiValidationError:
        return False
