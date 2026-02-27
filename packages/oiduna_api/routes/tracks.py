"""
Track management routes.
"""

from typing import Annotated, Any
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from oiduna_api.dependencies import get_session_manager
from oiduna_session import SessionManager, SessionValidator
from oiduna_models import Track


router = APIRouter()


# Request/Response models
class TrackCreateRequest(BaseModel):
    """Request body for creating a track."""
    track_name: str = Field(..., min_length=1, description="Human-readable track name")
    destination_id: str = Field(..., description="Target destination ID")
    base_params: dict[str, Any] = Field(
        default_factory=dict,
        description="Base parameters for all events"
    )


class TrackUpdateRequest(BaseModel):
    """Request body for updating track base params."""
    base_params: dict[str, Any] = Field(
        ...,
        description="Parameters to merge (shallow merge)"
    )


# Helper function for auth
async def verify_auth(
    x_client_id: str,
    x_client_token: str,
    manager: SessionManager,
) -> str:
    """Verify client authentication and return client_id."""
    client = manager.get_client(x_client_id)
    if not client or client.token != x_client_token:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return x_client_id


# Routes
@router.get(
    "/tracks",
    response_model=list[Track],
    summary="List all tracks"
)
async def list_tracks(
    x_client_id: Annotated[str, Header()],
    x_client_token: Annotated[str, Header()],
    manager: SessionManager = Depends(get_session_manager),
):
    """
    List all tracks in the session.

    Example:
        GET /tracks
        Headers:
            X-Client-ID: alice_001
            X-Client-Token: <token>
    """
    await verify_auth(x_client_id, x_client_token, manager)
    return manager.list_tracks()


@router.get(
    "/tracks/{track_id}",
    response_model=Track,
    summary="Get track details"
)
async def get_track(
    track_id: str,
    x_client_id: Annotated[str, Header()],
    x_client_token: Annotated[str, Header()],
    manager: SessionManager = Depends(get_session_manager),
):
    """
    Get detailed information about a track.

    Example:
        GET /tracks/track_001
        Headers:
            X-Client-ID: alice_001
            X-Client-Token: <token>
    """
    await verify_auth(x_client_id, x_client_token, manager)

    track = manager.get_track(track_id)
    if track is None:
        raise HTTPException(status_code=404, detail="Track not found")

    return track


@router.post(
    "/tracks/{track_id}",
    response_model=Track,
    status_code=201,
    summary="Create a new track"
)
async def create_track(
    track_id: str,
    req: TrackCreateRequest,
    x_client_id: Annotated[str, Header()],
    x_client_token: Annotated[str, Header()],
    manager: SessionManager = Depends(get_session_manager),
):
    """
    Create a new track.

    The track will be owned by the authenticated client.

    Example:
        POST /tracks/track_001
        Headers:
            X-Client-ID: alice_001
            X-Client-Token: <token>
        Body:
        {
            "track_name": "kick",
            "destination_id": "superdirt",
            "base_params": {"sound": "bd", "orbit": 0}
        }
    """
    client_id = await verify_auth(x_client_id, x_client_token, manager)

    try:
        track = manager.create_track(
            track_id=track_id,
            track_name=req.track_name,
            destination_id=req.destination_id,
            client_id=client_id,
            base_params=req.base_params,
        )
        return track
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch(
    "/tracks/{track_id}",
    response_model=Track,
    summary="Update track base parameters"
)
async def update_track(
    track_id: str,
    req: TrackUpdateRequest,
    x_client_id: Annotated[str, Header()],
    x_client_token: Annotated[str, Header()],
    manager: SessionManager = Depends(get_session_manager),
):
    """
    Update track base parameters (shallow merge).

    Only the owner can update a track.

    Example:
        PATCH /tracks/track_001
        Headers:
            X-Client-ID: alice_001
            X-Client-Token: <token>
        Body:
        {
            "base_params": {"gain": 0.8}
        }
    """
    client_id = await verify_auth(x_client_id, x_client_token, manager)

    # Check ownership
    validator = SessionValidator()
    if not validator.check_track_ownership(manager.session, track_id, client_id):
        raise HTTPException(
            status_code=403,
            detail="You don't own this track"
        )

    # Update track
    track = manager.update_track_base_params(track_id, req.base_params)
    if track is None:
        raise HTTPException(status_code=404, detail="Track not found")

    return track


@router.delete(
    "/tracks/{track_id}",
    status_code=204,
    summary="Delete a track"
)
async def delete_track(
    track_id: str,
    x_client_id: Annotated[str, Header()],
    x_client_token: Annotated[str, Header()],
    manager: SessionManager = Depends(get_session_manager),
):
    """
    Delete a track (including all its patterns).

    Only the owner can delete a track.

    Example:
        DELETE /tracks/track_001
        Headers:
            X-Client-ID: alice_001
            X-Client-Token: <token>
    """
    client_id = await verify_auth(x_client_id, x_client_token, manager)

    # Check ownership
    validator = SessionValidator()
    if not validator.check_track_ownership(manager.session, track_id, client_id):
        raise HTTPException(
            status_code=403,
            detail="You don't own this track"
        )

    # Delete track
    success = manager.delete_track(track_id)
    if not success:
        raise HTTPException(status_code=404, detail="Track not found")
