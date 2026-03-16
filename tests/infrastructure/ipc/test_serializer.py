"""Tests for IPCSerializer.

Tests cover:
- Round-trip serialization (msgpack and JSON)
- Message format validation
- Error handling
- Boundary values
- Data type support
"""

import pytest

try:
    import msgpack
    MSGPACK_AVAILABLE = True
except ImportError:
    MSGPACK_AVAILABLE = False
    msgpack = None  # type: ignore

from oiduna.infrastructure.ipc.serializer import IPCSerializer


class TestSerializerBasics:
    """Test basic serialization functionality."""

    def test_default_format_is_msgpack(self):
        """Test that default serialization format is msgpack."""
        serializer = IPCSerializer()
        assert serializer.format == "msgpack"

    def test_explicit_msgpack_format(self):
        """Test explicit msgpack format selection."""
        serializer = IPCSerializer(format="msgpack")
        assert serializer.format == "msgpack"

    def test_explicit_json_format(self):
        """Test explicit JSON format selection."""
        serializer = IPCSerializer(format="json")
        assert serializer.format == "json"


class TestRoundTripSerialization:
    """Test round-trip serialization for various data types."""

    @pytest.mark.parametrize("format", ["msgpack", "json"])
    def test_simple_dict(self, format):
        """Test serialization of simple dictionary."""
        serializer = IPCSerializer(format=format)
        data = {"key": "value", "num": 42}

        serialized = serializer.serialize(data)
        deserialized = serializer.deserialize(serialized)

        assert deserialized == data

    @pytest.mark.parametrize("format", ["msgpack", "json"])
    def test_nested_dict(self, format):
        """Test serialization of nested dictionary."""
        serializer = IPCSerializer(format=format)
        data = {
            "outer": {
                "inner": {
                    "deep": "value"
                }
            },
            "list": [1, 2, 3]
        }

        serialized = serializer.serialize(data)
        deserialized = serializer.deserialize(serialized)

        assert deserialized == data

    @pytest.mark.parametrize("format", ["msgpack", "json"])
    def test_various_data_types(self, format):
        """Test serialization of various data types."""
        serializer = IPCSerializer(format=format)
        data = {
            "int": 42,
            "float": 3.14,
            "string": "hello",
            "bool_true": True,
            "bool_false": False,
            "none": None,
            "list": [1, 2, 3],
            "nested_list": [[1, 2], [3, 4]],
            "empty_list": [],
            "empty_dict": {},
        }

        serialized = serializer.serialize(data)
        deserialized = serializer.deserialize(serialized)

        assert deserialized == data

    def test_msgpack_bytes_type(self):
        """Test msgpack handles bytes type correctly."""
        serializer = IPCSerializer(format="msgpack")
        data = {"bytes_data": b"binary\x00\xff"}

        serialized = serializer.serialize(data)
        deserialized = serializer.deserialize(serialized)

        assert deserialized == data
        assert isinstance(deserialized["bytes_data"], bytes)


class TestBoundaryValues:
    """Test serialization of boundary values."""

    @pytest.mark.parametrize("format", ["msgpack", "json"])
    @pytest.mark.parametrize("value", [
        0,
        -1,
        1,
        2**31 - 1,  # Max int32
        -(2**31),   # Min int32
        2**63 - 1,  # Max int64
        -(2**63),   # Min int64
    ])
    def test_integer_boundaries(self, format, value):
        """Test serialization of integer boundary values."""
        serializer = IPCSerializer(format=format)
        data = {"value": value}

        serialized = serializer.serialize(data)
        deserialized = serializer.deserialize(serialized)

        assert deserialized["value"] == value

    @pytest.mark.parametrize("format", ["msgpack", "json"])
    @pytest.mark.parametrize("value", [
        0.0,
        -0.0,
        1.0,
        -1.0,
        3.14159265359,
        1e10,
        1e-10,
        float("inf"),
        float("-inf"),
    ])
    def test_float_boundaries(self, format, value):
        """Test serialization of float boundary values."""
        serializer = IPCSerializer(format=format)
        data = {"value": value}

        serialized = serializer.serialize(data)
        deserialized = serializer.deserialize(serialized)

        # Handle NaN separately
        if value != value:  # NaN check
            assert deserialized["value"] != deserialized["value"]
        else:
            assert deserialized["value"] == value

    @pytest.mark.parametrize("format", ["msgpack", "json"])
    def test_float_nan(self, format):
        """Test serialization of NaN (special case)."""
        serializer = IPCSerializer(format=format)
        data = {"value": float("nan")}

        serialized = serializer.serialize(data)
        deserialized = serializer.deserialize(serialized)

        # NaN != NaN, so check using inequality
        assert deserialized["value"] != deserialized["value"]

    @pytest.mark.parametrize("format", ["msgpack", "json"])
    def test_empty_string(self, format):
        """Test serialization of empty string."""
        serializer = IPCSerializer(format=format)
        data = {"value": ""}

        serialized = serializer.serialize(data)
        deserialized = serializer.deserialize(serialized)

        assert deserialized == data

    @pytest.mark.parametrize("format", ["msgpack", "json"])
    def test_unicode_string(self, format):
        """Test serialization of unicode strings."""
        serializer = IPCSerializer(format=format)
        data = {"value": "Hello 世界 🎵 Ødúná"}

        serialized = serializer.serialize(data)
        deserialized = serializer.deserialize(serialized)

        assert deserialized == data

    @pytest.mark.parametrize("format", ["msgpack", "json"])
    def test_large_dict(self, format):
        """Test serialization of large dictionary (1000+ keys)."""
        serializer = IPCSerializer(format=format)
        data = {f"key_{i}": i for i in range(1000)}

        serialized = serializer.serialize(data)
        deserialized = serializer.deserialize(serialized)

        assert deserialized == data


class TestMessageFormat:
    """Test message format validation."""

    @pytest.mark.parametrize("format", ["msgpack", "json"])
    def test_serialize_message_structure(self, format):
        """Test that serialize_message creates correct structure."""
        serializer = IPCSerializer(format=format)
        msg_type = "compile"
        payload = {"track_id": "t1", "pattern": "bd*4"}

        serialized = serializer.serialize_message(msg_type, payload)
        deserialized = serializer.deserialize(serialized)

        assert "type" in deserialized
        assert "payload" in deserialized
        assert deserialized["type"] == msg_type
        assert deserialized["payload"] == payload

    @pytest.mark.parametrize("format", ["msgpack", "json"])
    def test_serialize_message_empty_payload(self, format):
        """Test serialize_message with no payload (defaults to empty dict)."""
        serializer = IPCSerializer(format=format)
        msg_type = "stop"

        serialized = serializer.serialize_message(msg_type)
        deserialized = serializer.deserialize(serialized)

        assert deserialized["type"] == msg_type
        assert deserialized["payload"] == {}

    @pytest.mark.parametrize("format", ["msgpack", "json"])
    def test_serialize_message_none_payload(self, format):
        """Test serialize_message with explicit None payload."""
        serializer = IPCSerializer(format=format)
        msg_type = "pause"

        serialized = serializer.serialize_message(msg_type, None)
        deserialized = serializer.deserialize(serialized)

        assert deserialized["type"] == msg_type
        assert deserialized["payload"] == {}

    @pytest.mark.parametrize("format", ["msgpack", "json"])
    def test_deserialize_message_extraction(self, format):
        """Test deserialize_message extracts type and payload."""
        serializer = IPCSerializer(format=format)
        msg_type = "play"
        payload = {"position": 0}

        serialized = serializer.serialize_message(msg_type, payload)
        extracted_type, extracted_payload = serializer.deserialize_message(serialized)

        assert extracted_type == msg_type
        assert extracted_payload == payload

    @pytest.mark.parametrize("format", ["msgpack", "json"])
    def test_deserialize_message_missing_type(self, format):
        """Test deserialize_message with missing type field."""
        serializer = IPCSerializer(format=format)
        data = {"payload": {"key": "value"}}

        serialized = serializer.serialize(data)
        msg_type, payload = serializer.deserialize_message(serialized)

        assert msg_type == ""
        assert payload == {"key": "value"}

    @pytest.mark.parametrize("format", ["msgpack", "json"])
    def test_deserialize_message_missing_payload(self, format):
        """Test deserialize_message with missing payload field."""
        serializer = IPCSerializer(format=format)
        data = {"type": "status"}

        serialized = serializer.serialize(data)
        msg_type, payload = serializer.deserialize_message(serialized)

        assert msg_type == "status"
        assert payload == {}


class TestErrorHandling:
    """Test error handling in serialization."""

    def test_deserialize_invalid_json(self):
        """Test deserializing invalid JSON bytes."""
        serializer = IPCSerializer(format="json")

        with pytest.raises(Exception):  # json.JSONDecodeError
            serializer.deserialize(b"not valid json")

    def test_deserialize_invalid_msgpack(self):
        """Test deserializing invalid msgpack bytes."""
        serializer = IPCSerializer(format="msgpack")

        with pytest.raises(Exception):  # msgpack.exceptions.ExtraData or similar
            serializer.deserialize(b"\xff\xff\xff\xff")

    def test_deserialize_non_dict_json(self):
        """Test deserializing JSON that is not a dict."""
        serializer = IPCSerializer(format="json")

        with pytest.raises(ValueError, match="Expected dict"):
            serializer.deserialize(b"[1, 2, 3]")

    def test_deserialize_non_dict_msgpack(self):
        """Test deserializing msgpack that is not a dict."""
        serializer = IPCSerializer(format="msgpack")
        serialized_list = msgpack.packb([1, 2, 3], use_bin_type=True)

        with pytest.raises(ValueError, match="Expected dict"):
            serializer.deserialize(serialized_list)

    def test_deserialize_string_msgpack(self):
        """Test deserializing msgpack string (not a dict)."""
        serializer = IPCSerializer(format="msgpack")
        serialized_str = msgpack.packb("hello", use_bin_type=True)

        with pytest.raises(ValueError, match="Expected dict"):
            serializer.deserialize(serialized_str)

    def test_deserialize_number_json(self):
        """Test deserializing JSON number (not a dict)."""
        serializer = IPCSerializer(format="json")

        with pytest.raises(ValueError, match="Expected dict"):
            serializer.deserialize(b"42")


class TestFormatConsistency:
    """Test that format selection is consistent."""

    def test_msgpack_produces_bytes(self):
        """Test that msgpack serialization produces bytes."""
        serializer = IPCSerializer(format="msgpack")
        data = {"key": "value"}

        result = serializer.serialize(data)

        assert isinstance(result, bytes)

    def test_json_produces_bytes(self):
        """Test that JSON serialization produces bytes."""
        serializer = IPCSerializer(format="json")
        data = {"key": "value"}

        result = serializer.serialize(data)

        assert isinstance(result, bytes)

    def test_format_immutable_after_init(self):
        """Test that format property is read-only."""
        serializer = IPCSerializer(format="msgpack")

        assert serializer.format == "msgpack"

        # Format property should be read-only (no setter)
        # This test verifies it's accessible but not settable
        with pytest.raises(AttributeError):
            serializer.format = "json"
