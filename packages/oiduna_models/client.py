"""
ClientInfo model for client authentication and metadata.

Clients represent users or applications connected to Oiduna.
Each client has a unique token for authentication.
"""

from typing import Any, Literal
from pydantic import BaseModel, Field
import uuid


class ClientInfo(BaseModel):
    """
    Client information with authentication token.

    All fields are immutable after creation (except token expiry in future).

    Attributes:
        client_id: Unique identifier (user-provided)
        client_name: Human-readable name
        token: UUID token for authentication (generated at creation)
        distribution: Client type ("mars", "web", "mobile", etc.)
        metadata: Additional client-specific metadata

    Example:
        >>> client = ClientInfo(
        ...     client_id="client_001",
        ...     client_name="Alice's MARS",
        ...     token=str(uuid.uuid4()),
        ...     distribution="mars",
        ...     metadata={"version": "0.1.0"}
        ... )
    """

    # All fields immutable after creation
    client_id: str = Field(
        ...,
        min_length=1,
        description="Unique client identifier"
    )
    client_name: str = Field(
        ...,
        min_length=1,
        description="Human-readable client name"
    )
    token: str = Field(
        ...,
        description="UUID authentication token"
    )
    distribution: str = Field(
        default="unknown",
        description="Client distribution type (mars, web, mobile, etc.)"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional client metadata"
    )

    @staticmethod
    def generate_token() -> str:
        """Generate a new UUID token."""
        return str(uuid.uuid4())

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "client_id": "client_001",
                    "client_name": "Alice's MARS",
                    "token": "550e8400-e29b-41d4-a716-446655440000",
                    "distribution": "mars",
                    "metadata": {"version": "0.1.0"}
                }
            ]
        }
    }
