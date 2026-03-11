"""
Authentication routes for client registration and management.
"""

from typing import Annotated, Any
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field

from oiduna.application.api.dependencies import get_container
from oiduna.domain.session import SessionContainer


router = APIRouter()


# Request/Response models
class ClientCreateRequest(BaseModel):
    """Request body for creating a client."""
    client_name: str = Field(..., min_length=1, description="Human-readable client name")
    distribution: str = Field(default="unknown", description="Client type (mars, web, etc.)")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ClientResponse(BaseModel):
    """Response with client info (includes token only on creation)."""
    client_id: str
    client_name: str
    distribution: str
    metadata: dict[str, Any]
    token: str | None = Field(
        default=None,
        description="Token only returned on creation"
    )


class ClientInfoResponse(BaseModel):
    """Response with client info (no token)."""
    client_id: str
    client_name: str
    distribution: str
    metadata: dict[str, Any]


# Routes
@router.post(
    "/clients/{client_id}",
    response_model=ClientResponse,
    status_code=201,
    summary="Register a new client"
)
async def create_client(
    client_id: str,
    req: ClientCreateRequest,
    container: SessionContainer = Depends(get_container),
):
    """
    Register a new client and receive an authentication token.

    The token is only returned once during registration.
    Store it securely and use it in X-Client-Token header for all requests.

    Example:
        POST /clients/alice_001
        {
            "client_name": "Alice's MARS",
            "distribution": "mars",
            "metadata": {"version": "0.1.0"}
        }

        Response:
        {
            "client_id": "alice_001",
            "client_name": "Alice's MARS",
            "token": "550e8400-e29b-41d4-a716-446655440000",
            "distribution": "mars",
            "metadata": {"version": "0.1.0"}
        }
    """
    try:
        client = container.clients.create(
            client_id=client_id,
            client_name=req.client_name,
            distribution=req.distribution,
            metadata=req.metadata,
        )
        return ClientResponse(
            client_id=client.client_id,
            client_name=client.client_name,
            distribution=client.distribution,
            metadata=client.metadata,
            token=client.token,  # Only returned on creation
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get(
    "/clients",
    response_model=list[ClientInfoResponse],
    summary="List all connected clients"
)
async def list_clients(
    container: SessionContainer = Depends(get_container),
):
    """
    List all connected clients (without tokens).

    Example:
        GET /clients

        Response:
        [
            {
                "client_id": "alice_001",
                "client_name": "Alice's MARS",
                "distribution": "mars",
                "metadata": {}
            }
        ]
    """
    clients = container.clients.list_clients()
    return [
        ClientInfoResponse(
            client_id=c.client_id,
            client_name=c.client_name,
            distribution=c.distribution,
            metadata=c.metadata,
        )
        for c in clients
    ]


@router.get(
    "/clients/{client_id}",
    response_model=ClientInfoResponse,
    summary="Get client information"
)
async def get_client(
    client_id: str,
    container: SessionContainer = Depends(get_container),
):
    """
    Get information about a specific client (without token).

    Example:
        GET /clients/alice_001

        Response:
        {
            "client_id": "alice_001",
            "client_name": "Alice's MARS",
            "distribution": "mars",
            "metadata": {}
        }
    """
    client = container.clients.get(client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")

    return ClientInfoResponse(
        client_id=client.client_id,
        client_name=client.client_name,
        distribution=client.distribution,
        metadata=client.metadata,
    )


@router.delete(
    "/clients/{client_id}",
    status_code=204,
    summary="Disconnect (self-delete)"
)
async def delete_client(
    client_id: str,
    x_client_id: Annotated[str, Header()],
    x_client_token: Annotated[str, Header()],
    container: SessionContainer = Depends(get_container),
):
    """
    Disconnect a client (self-delete only).

    Clients can only delete themselves.
    Requires authentication headers.

    Note: This does NOT delete tracks/patterns owned by the client.
    Use admin endpoints for full cleanup.

    Example:
        DELETE /clients/alice_001
        Headers:
            X-Client-ID: alice_001
            X-Client-Token: <token>
    """
    # Verify authentication
    client = container.clients.get(x_client_id)
    if not client or client.token != x_client_token:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Verify ownership (can only delete self)
    if x_client_id != client_id:
        raise HTTPException(
            status_code=403,
            detail="Can only delete your own client"
        )

    # Delete client
    success = container.clients.delete(client_id)
    if not success:
        raise HTTPException(status_code=404, detail="Client not found")
