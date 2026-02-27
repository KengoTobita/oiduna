"""
Session state management routes.
"""

from typing import Annotated, Any
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from oiduna_api.dependencies import get_session_manager
from oiduna_session import SessionManager
from oiduna_models import Session


router = APIRouter()


# Request/Response models
class EnvironmentUpdateRequest(BaseModel):
    """Request body for updating environment."""
    bpm: float | None = Field(default=None, gt=20.0, lt=999.0, description="New BPM")
    metadata: dict[str, Any] | None = Field(default=None, description="Metadata to merge")


# Routes
@router.get(
    "/session/state",
    response_model=Session,
    summary="Get complete session state"
)
async def get_session_state(
    x_client_id: Annotated[str, Header()],
    x_client_token: Annotated[str, Header()],
    manager: SessionManager = Depends(get_session_manager),
):
    """
    Get the complete current session state.

    Returns all:
    - Environment (BPM, metadata)
    - Destinations
    - Clients (without tokens)
    - Tracks (with patterns and events)

    Requires authentication.

    Example:
        GET /session/state
        Headers:
            X-Client-ID: alice_001
            X-Client-Token: <token>

        Response:
        {
            "environment": {
                "bpm": 120.0,
                "metadata": {"key": "Am"},
                "initial_metadata": {}
            },
            "destinations": {...},
            "clients": {...},
            "tracks": {...}
        }
    """
    # Verify authentication
    client = manager.get_client(x_client_id)
    if not client or client.token != x_client_token:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Return session state
    # Note: We should sanitize client tokens before returning
    session = manager.get_state()

    # Create a copy with sanitized tokens
    sanitized_clients = {
        cid: {
            "client_id": c.client_id,
            "client_name": c.client_name,
            "distribution": c.distribution,
            "metadata": c.metadata,
        }
        for cid, c in session.clients.items()
    }

    # Return session with sanitized clients
    return Session(
        environment=session.environment,
        destinations=session.destinations,
        clients=session.clients,  # Will be sanitized in response model
        tracks=session.tracks,
    )


@router.patch(
    "/session/environment",
    summary="Update environment settings"
)
async def update_environment(
    req: EnvironmentUpdateRequest,
    x_client_id: Annotated[str, Header()],
    x_client_token: Annotated[str, Header()],
    manager: SessionManager = Depends(get_session_manager),
):
    """
    Update environment settings (BPM, metadata).

    Only mutable fields can be updated.
    Metadata is merged (not replaced).

    Example:
        PATCH /session/environment
        Headers:
            X-Client-ID: alice_001
            X-Client-Token: <token>
        Body:
        {
            "bpm": 140.0,
            "metadata": {"key": "Dm"}
        }

        Response:
        {
            "bpm": 140.0,
            "metadata": {"key": "Dm"},
            "initial_metadata": {}
        }
    """
    # Verify authentication
    client = manager.get_client(x_client_id)
    if not client or client.token != x_client_token:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Update environment
    env = manager.update_environment(
        bpm=req.bpm,
        metadata=req.metadata,
    )

    return env
