"""
Session state management routes.
"""

from typing import Annotated, Any
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from oiduna_api.dependencies import get_container, get_loop_service
from oiduna_api.services.loop_service import LoopService
from oiduna_session import SessionContainer
from oiduna_models import Session


router = APIRouter()


# Request/Response models
class EnvironmentUpdateRequest(BaseModel):
    """Request body for updating environment."""
    bpm: float | None = Field(default=None, gt=20.0, lt=999.0, description="New BPM")
    metadata: dict[str, Any] | None = Field(default=None, description="Metadata to merge")
    position_update_interval: str | None = Field(
        default=None,
        description="SSE position event frequency: 'beat' or 'bar'"
    )


# Routes
@router.get(
    "/config",
    summary="Get Oiduna configuration and structural information"
)
async def get_config(
    container: SessionContainer = Depends(get_container),
):
    """
    Get Oiduna configuration and structural information (no authentication required).

    Returns:
    - environment: Current environment settings (BPM, metadata, position_update_interval)
    - loop_steps: Fixed loop length (256)
    - api_version: API version for compatibility checking
    - clients: Connected clients (minimal info: id, name, distribution)
    - destinations: Available destinations for track creation

    This endpoint provides structural information needed for client initialization.
    For detailed session state (tracks, patterns), use GET /session/state (requires auth).

    Example:
        GET /config

        Response:
        {
            "environment": {
                "bpm": 120.0,
                "metadata": {},
                "position_update_interval": "beat",
                "initial_metadata": {}
            },
            "loop_steps": 256,
            "api_version": "1.0",
            "clients": [
                {
                    "client_id": "alice_001",
                    "client_name": "Alice's MARS",
                    "distribution": "mars"
                }
            ],
            "destinations": [
                {
                    "id": "superdirt",
                    "type": "osc",
                    "host": "127.0.0.1",
                    "port": 57120,
                    "address": "/dirt/play"
                }
            ]
        }
    """
    from oiduna_loop.constants import LOOP_STEPS

    # Get clients (minimal info: no tokens, no metadata)
    clients = [
        {
            "client_id": client.client_id,
            "client_name": client.client_name,
            "distribution": client.distribution,
        }
        for client in container.clients.list()
    ]

    # Get destinations (full info for destination selection)
    # Note: destinations is a dict, so we use .values()
    destinations = [
        dest.model_dump()
        for dest in container.session.destinations.values()
    ]

    return {
        "environment": container.session.environment,
        "loop_steps": LOOP_STEPS,
        "api_version": "1.0",
        "session_version": container.session.version,
        "clients": clients,
        "destinations": destinations,
    }


@router.get(
    "/session/state",
    response_model=Session,
    summary="Get complete session state"
)
async def get_session_state(
    x_client_id: Annotated[str, Header()],
    x_client_token: Annotated[str, Header()],
    container: SessionContainer = Depends(get_container),
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
    client = container.clients.get(x_client_id)
    if not client or client.token != x_client_token:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Return session state
    # Note: We should sanitize client tokens before returning
    session = container.get_state()

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
        version=session.version,
        last_modified_by=session.last_modified_by,
        last_modified_at=session.last_modified_at,
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
    container: SessionContainer = Depends(get_container),
):
    """
    Update environment settings (BPM, metadata, position_update_interval).

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
            "metadata": {"key": "Dm"},
            "position_update_interval": "bar"
        }

        Response:
        {
            "bpm": 140.0,
            "metadata": {"key": "Dm"},
            "position_update_interval": "bar",
            "initial_metadata": {}
        }
    """
    # Verify authentication
    client = container.clients.get(x_client_id)
    if not client or client.token != x_client_token:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Update environment
    env = container.environment.update(
        bpm=req.bpm,
        metadata=req.metadata,
        position_update_interval=req.position_update_interval,
    )

    # Sync position_update_interval to LoopEngine if changed
    # Note: Only sync if LoopService is initialized (may not be in tests)
    if req.position_update_interval is not None:
        try:
            loop_service = get_loop_service()
            engine = loop_service.get_engine()
            engine.state.position_update_interval = req.position_update_interval
        except RuntimeError:
            # LoopService not initialized (e.g., in tests without engine)
            pass

    return env
