"""
Track management routes.
"""

from typing import Annotated, Any
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field, field_validator

from oiduna.application.api.dependencies import get_container
from oiduna.domain.session import SessionContainer, SessionValidator
from oiduna.domain.models import Track


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

    @field_validator("destination_id")
    @classmethod
    def validate_destination_id(cls, v: str) -> str:
        """
        Validate destination ID format.

        Args:
            v: The destination_id to validate

        Returns:
            The validated destination_id

        Raises:
            ValueError: If destination_id contains invalid characters
        """
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                f"Destination ID must be alphanumeric with underscores or hyphens. "
                f"Got: '{v}'. "
                f"Valid examples: 'superdirt', 'midi_1', 'osc-synth'"
            )
        return v


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
    container: SessionContainer,
) -> str:
    """Verify client authentication and return client_id."""
    client = container.clients.get(x_client_id)
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
    container: SessionContainer = Depends(get_container),
):
    """
    List all tracks in the session.

    Example:
        GET /tracks
        Headers:
            X-Client-ID: alice_001
            X-Client-Token: <token>
    """
    await verify_auth(x_client_id, x_client_token, container)
    return container.tracks.list_tracks()


@router.get(
    "/tracks/{track_id}",
    response_model=Track,
    summary="Get track details"
)
async def get_track(
    track_id: str,
    x_client_id: Annotated[str, Header()],
    x_client_token: Annotated[str, Header()],
    container: SessionContainer = Depends(get_container),
):
    """
    Get detailed information about a track.

    Example:
        GET /tracks/track_001
        Headers:
            X-Client-ID: alice_001
            X-Client-Token: <token>
    """
    await verify_auth(x_client_id, x_client_token, container)

    track = container.tracks.get(track_id)
    if track is None:
        raise HTTPException(status_code=404, detail="Track not found")

    return track


@router.post(
    "/tracks",
    response_model=Track,
    status_code=201,
    summary="Create a new track"
)
async def create_track(
    req: TrackCreateRequest,
    x_client_id: Annotated[str, Header()],
    x_client_token: Annotated[str, Header()],
    container: SessionContainer = Depends(get_container),
):
    """
    Create a new track with server-generated ID.

    The track will be owned by the authenticated client.
    The server generates a unique 8-digit hexadecimal track_id.

    Example:
        POST /tracks
        Headers:
            X-Client-ID: alice_001
            X-Client-Token: <token>
        Body:
        {
            "track_name": "kick",
            "destination_id": "superdirt",
            "base_params": {"sound": "bd", "orbit": 0}
        }

        Response:
        {
            "track_id": "a1b2c3d4",
            "track_name": "kick",
            "destination_id": "superdirt",
            "client_id": "alice_001",
            "base_params": {"sound": "bd", "orbit": 0},
            "patterns": {}
        }
    """
    client_id = await verify_auth(x_client_id, x_client_token, container)

    try:
        track = container.tracks.create(
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
    container: SessionContainer = Depends(get_container),
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
    client_id = await verify_auth(x_client_id, x_client_token, container)

    # Check ownership
    validator = SessionValidator()
    if not validator.check_track_ownership(container.session, track_id, client_id):
        raise HTTPException(
            status_code=403,
            detail="You don't own this track"
        )

    # Update track
    track = container.tracks.update_base_params(track_id, req.base_params)
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
    container: SessionContainer = Depends(get_container),
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
    client_id = await verify_auth(x_client_id, x_client_token, container)

    # Check ownership
    validator = SessionValidator()
    if not validator.check_track_ownership(container.session, track_id, client_id):
        raise HTTPException(
            status_code=403,
            detail="You don't own this track"
        )

    # Delete track
    success = container.tracks.delete(track_id)
    if not success:
        raise HTTPException(status_code=404, detail="Track not found")
