"""
Pattern management routes.
"""

from typing import Annotated
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from oiduna_api.dependencies import get_container
from oiduna_session import SessionContainer, SessionValidator
from oiduna_models import Pattern, Event


router = APIRouter()


# Request/Response models
class PatternCreateRequest(BaseModel):
    """Request body for creating a pattern."""
    pattern_name: str = Field(..., min_length=1, description="Human-readable pattern name")
    active: bool = Field(default=True, description="Whether pattern is active")
    events: list[Event] = Field(default_factory=list, description="Pattern events")


class PatternUpdateRequest(BaseModel):
    """Request body for updating a pattern."""
    active: bool | None = Field(default=None, description="New active state")
    events: list[Event] | None = Field(default=None, description="New events list")


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
    "/tracks/{track_id}/patterns",
    response_model=list[Pattern],
    summary="List all patterns in a track"
)
async def list_patterns(
    track_id: str,
    x_client_id: Annotated[str, Header()],
    x_client_token: Annotated[str, Header()],
    container: SessionContainer = Depends(get_container),
):
    """
    List all patterns in a track.

    Example:
        GET /tracks/track_001/patterns
        Headers:
            X-Client-ID: alice_001
            X-Client-Token: <token>
    """
    await verify_auth(x_client_id, x_client_token, container)

    patterns = container.patterns.list(track_id)
    if patterns is None:
        raise HTTPException(status_code=404, detail="Track not found")

    return patterns


@router.get(
    "/tracks/{track_id}/patterns/{pattern_id}",
    response_model=Pattern,
    summary="Get pattern details"
)
async def get_pattern(
    track_id: str,
    pattern_id: str,
    x_client_id: Annotated[str, Header()],
    x_client_token: Annotated[str, Header()],
    container: SessionContainer = Depends(get_container),
):
    """
    Get detailed information about a pattern.

    Example:
        GET /tracks/track_001/patterns/pattern_001
        Headers:
            X-Client-ID: alice_001
            X-Client-Token: <token>
    """
    await verify_auth(x_client_id, x_client_token, container)

    pattern = container.patterns.get(track_id, pattern_id)
    if pattern is None:
        raise HTTPException(status_code=404, detail="Pattern not found")

    return pattern


@router.post(
    "/tracks/{track_id}/patterns/{pattern_id}",
    response_model=Pattern,
    status_code=201,
    summary="Create a new pattern"
)
async def create_pattern(
    track_id: str,
    pattern_id: str,
    req: PatternCreateRequest,
    x_client_id: Annotated[str, Header()],
    x_client_token: Annotated[str, Header()],
    container: SessionContainer = Depends(get_container),
):
    """
    Create a new pattern in a track.

    The pattern will be owned by the authenticated client.
    Note: Pattern ownership is independent of track ownership.

    Example:
        POST /tracks/track_001/patterns/pattern_001
        Headers:
            X-Client-ID: alice_001
            X-Client-Token: <token>
        Body:
        {
            "pattern_name": "main_beat",
            "active": true,
            "events": [
                {"step": 0, "cycle": 0.0, "params": {}},
                {"step": 64, "cycle": 1.0, "params": {"gain": 0.9}}
            ]
        }
    """
    client_id = await verify_auth(x_client_id, x_client_token, container)

    try:
        pattern = container.patterns.create(
            track_id=track_id,
            pattern_id=pattern_id,
            pattern_name=req.pattern_name,
            client_id=client_id,
            active=req.active,
            events=req.events,
        )
        if pattern is None:
            raise HTTPException(status_code=404, detail="Track not found")
        return pattern
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch(
    "/tracks/{track_id}/patterns/{pattern_id}",
    response_model=Pattern,
    summary="Update a pattern"
)
async def update_pattern(
    track_id: str,
    pattern_id: str,
    req: PatternUpdateRequest,
    x_client_id: Annotated[str, Header()],
    x_client_token: Annotated[str, Header()],
    container: SessionContainer = Depends(get_container),
):
    """
    Update a pattern (active state and/or events).

    Only the track owner can update patterns.
    (This ensures track owners control all patterns in their tracks)

    Example:
        PATCH /tracks/track_001/patterns/pattern_001
        Headers:
            X-Client-ID: alice_001
            X-Client-Token: <token>
        Body:
        {
            "active": false
        }
    """
    client_id = await verify_auth(x_client_id, x_client_token, container)

    # Check track ownership (track owner can edit all patterns)
    validator = SessionValidator()
    if not validator.check_track_ownership(container.session, track_id, client_id):
        raise HTTPException(
            status_code=403,
            detail="Only track owner can edit patterns"
        )

    # Update pattern
    pattern = container.patterns.update(
        track_id=track_id,
        pattern_id=pattern_id,
        active=req.active,
        events=req.events,
    )
    if pattern is None:
        raise HTTPException(status_code=404, detail="Pattern not found")

    return pattern


@router.delete(
    "/tracks/{track_id}/patterns/{pattern_id}",
    status_code=204,
    summary="Delete a pattern"
)
async def delete_pattern(
    track_id: str,
    pattern_id: str,
    x_client_id: Annotated[str, Header()],
    x_client_token: Annotated[str, Header()],
    container: SessionContainer = Depends(get_container),
):
    """
    Delete a pattern.

    Only the track owner can delete patterns.

    Example:
        DELETE /tracks/track_001/patterns/pattern_001
        Headers:
            X-Client-ID: alice_001
            X-Client-Token: <token>
    """
    client_id = await verify_auth(x_client_id, x_client_token, container)

    # Check track ownership
    validator = SessionValidator()
    if not validator.check_track_ownership(container.session, track_id, client_id):
        raise HTTPException(
            status_code=403,
            detail="Only track owner can delete patterns"
        )

    # Delete pattern
    success = container.patterns.delete(track_id, pattern_id)
    if not success:
        raise HTTPException(status_code=404, detail="Pattern not found")
