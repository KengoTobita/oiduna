"""
Pattern management routes (flat + hierarchical APIs).
"""

from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field

from oiduna_api.dependencies import get_container
from oiduna_session import SessionContainer, SessionValidator
from oiduna_models import Pattern, PatternEvent


router = APIRouter()


# Request/Response models
class PatternCreateRequest(BaseModel):
    """Request body for creating a pattern."""
    track_id: Optional[str] = Field(None, description="Parent track ID (4-digit hex, required for flat API)")
    pattern_name: str = Field(..., min_length=1, description="Human-readable pattern name")
    active: bool = Field(default=True, description="Whether pattern is active")
    events: list[PatternEvent] = Field(default_factory=list, description="Pattern events")


class PatternUpdateRequest(BaseModel):
    """Request body for updating a pattern."""
    track_id: Optional[str] = Field(None, description="New track ID (moves pattern)")
    active: Optional[bool] = Field(None, description="New active state")
    archived: Optional[bool] = Field(None, description="Soft delete/restore flag")
    events: Optional[list[PatternEvent]] = Field(None, description="New events list")


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


# ============================================================================
# FLAT PATTERN API (pattern_id only)
# ============================================================================

@router.get(
    "/patterns",
    response_model=list[Pattern],
    summary="List all patterns (flat API)"
)
async def list_all_patterns(
    x_client_id: Annotated[str, Header()],
    x_client_token: Annotated[str, Header()],
    container: SessionContainer = Depends(get_container),
    include_archived: bool = Query(False, description="Include archived patterns"),
):
    """
    List all patterns across all tracks.

    Query Parameters:
        include_archived: Include patterns with archived=True (default: false)

    Examples:
        GET /patterns
        GET /patterns?include_archived=true

    Returns:
        List of patterns (archived=false by default)
    """
    await verify_auth(x_client_id, x_client_token, container)
    return container.patterns.list_all(include_archived=include_archived)


@router.get(
    "/patterns/{pattern_id}",
    response_model=Pattern,
    summary="Get pattern by ID (flat API)"
)
async def get_pattern_by_id(
    pattern_id: str,
    x_client_id: Annotated[str, Header()],
    x_client_token: Annotated[str, Header()],
    container: SessionContainer = Depends(get_container),
):
    """
    Get pattern by pattern_id only (no track_id needed).

    ⚠️  Returns pattern even if archived=True

    Example:
        GET /patterns/3e2b
        Headers:
            X-Client-ID: alice
            X-Client-Token: <token>
    """
    await verify_auth(x_client_id, x_client_token, container)

    pattern = container.patterns.get_by_id(pattern_id)
    if pattern is None:
        raise HTTPException(status_code=404, detail="Pattern not found")

    return pattern


@router.post(
    "/patterns",
    response_model=Pattern,
    status_code=201,
    summary="Create pattern (flat API)"
)
async def create_pattern_flat(
    req: PatternCreateRequest,
    x_client_id: Annotated[str, Header()],
    x_client_token: Annotated[str, Header()],
    container: SessionContainer = Depends(get_container),
):
    """
    Create a new pattern with server-generated ID.

    Request Body:
        track_id: Required - parent track ID
        pattern_name: Required - human-readable name
        active: Optional (default: true)
        events: Optional (default: [])

    Example:
        POST /patterns
        Headers:
            X-Client-ID: alice
            X-Client-Token: <token>
        Body:
        {
            "track_id": "0a1f",
            "pattern_name": "main",
            "active": true,
            "events": []
        }

        Response:
        {
            "pattern_id": "3e2b",
            "track_id": "0a1f",
            "pattern_name": "main",
            "client_id": "alice",
            "active": true,
            "archived": false,
            "events": []
        }
    """
    client_id = await verify_auth(x_client_id, x_client_token, container)

    if not req.track_id:
        raise HTTPException(status_code=400, detail="track_id is required for flat API")

    try:
        pattern = container.patterns.create(
            track_id=req.track_id,
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
    "/patterns/{pattern_id}",
    response_model=Pattern,
    summary="Update pattern (flat API)"
)
async def update_pattern_flat(
    pattern_id: str,
    req: PatternUpdateRequest,
    x_client_id: Annotated[str, Header()],
    x_client_token: Annotated[str, Header()],
    container: SessionContainer = Depends(get_container),
):
    """
    Update pattern by pattern_id.

    ⚠️  Can update even if archived=True (for restoration)

    Request Body (all optional):
        track_id: Move pattern to different track
        active: Change演奏ON/OFF state
        archived: Soft delete/restore (true=archive, false=restore)
        events: Replace events

    Examples:
        # Mute
        PATCH /patterns/3e2b
        Body: {"active": false}

        # Restore from archive
        PATCH /patterns/3e2b
        Body: {"archived": false, "active": true}

        # Move to different track (楽器入れ替え)
        PATCH /patterns/3e2b
        Body: {"track_id": "0b2c"}

    Ownership:
        Only pattern owner can update
    """
    client_id = await verify_auth(x_client_id, x_client_token, container)

    # Check ownership
    pattern = container.patterns.get_by_id(pattern_id)
    if pattern is None:
        raise HTTPException(status_code=404, detail="Pattern not found")
    if pattern.client_id != client_id:
        raise HTTPException(status_code=403, detail="You don't own this pattern")

    # Update
    try:
        updated = container.patterns.update(
            pattern_id=pattern_id,
            track_id=req.track_id,
            active=req.active,
            archived=req.archived,
            events=req.events,
        )
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    "/patterns/{pattern_id}",
    status_code=204,
    summary="Delete pattern (flat API)"
)
async def delete_pattern_flat(
    pattern_id: str,
    x_client_id: Annotated[str, Header()],
    x_client_token: Annotated[str, Header()],
    container: SessionContainer = Depends(get_container),
):
    """
    Soft delete a pattern (set archived=True).

    Does not physically remove - just marks as archived.
    Pattern can be restored via PATCH with {"archived": false}.

    Ownership:
        Only pattern owner can delete

    Example:
        DELETE /patterns/3e2b
        Headers:
            X-Client-ID: alice
            X-Client-Token: <token>
    """
    client_id = await verify_auth(x_client_id, x_client_token, container)

    # Check ownership
    pattern = container.patterns.get_by_id(pattern_id)
    if pattern is None:
        raise HTTPException(status_code=404, detail="Pattern not found")
    if pattern.client_id != client_id:
        raise HTTPException(status_code=403, detail="You don't own this pattern")

    # Soft delete
    success = container.patterns.delete(pattern_id)
    if not success:
        raise HTTPException(status_code=404, detail="Pattern not found")


# ============================================================================
# HIERARCHICAL PATTERN API (track_id + pattern_id)
# ============================================================================

@router.get(
    "/tracks/{track_id}/patterns",
    response_model=list[Pattern],
    summary="List patterns in track (hierarchical API)"
)
async def list_patterns_in_track(
    track_id: str,
    x_client_id: Annotated[str, Header()],
    x_client_token: Annotated[str, Header()],
    container: SessionContainer = Depends(get_container),
    include_archived: bool = Query(False, description="Include archived patterns"),
):
    """
    List all patterns in a track.

    Query Parameters:
        include_archived: Include patterns with archived=True

    Example:
        GET /tracks/0a1f/patterns
        GET /tracks/0a1f/patterns?include_archived=true
        Headers:
            X-Client-ID: alice
            X-Client-Token: <token>
    """
    await verify_auth(x_client_id, x_client_token, container)

    patterns = container.patterns.list(track_id, include_archived=include_archived)
    if patterns is None:
        raise HTTPException(status_code=404, detail="Track not found")

    return patterns


@router.get(
    "/tracks/{track_id}/patterns/{pattern_id}",
    response_model=Pattern,
    summary="Get pattern (hierarchical API)"
)
async def get_pattern_hierarchical(
    track_id: str,
    pattern_id: str,
    x_client_id: Annotated[str, Header()],
    x_client_token: Annotated[str, Header()],
    container: SessionContainer = Depends(get_container),
):
    """
    Get pattern by track_id + pattern_id.

    Example:
        GET /tracks/0a1f/patterns/3e2b
        Headers:
            X-Client-ID: alice
            X-Client-Token: <token>
    """
    await verify_auth(x_client_id, x_client_token, container)

    pattern = container.patterns.get(track_id, pattern_id)
    if pattern is None:
        raise HTTPException(status_code=404, detail="Pattern not found")

    return pattern


@router.post(
    "/tracks/{track_id}/patterns",
    response_model=Pattern,
    status_code=201,
    summary="Create pattern (hierarchical API)"
)
async def create_pattern_hierarchical(
    track_id: str,
    req: PatternCreateRequest,
    x_client_id: Annotated[str, Header()],
    x_client_token: Annotated[str, Header()],
    container: SessionContainer = Depends(get_container),
):
    """
    Create a new pattern in a track with server-generated ID (hierarchical API).

    Request Body:
        pattern_name: Required - human-readable name
        active: Optional (default: true)
        events: Optional (default: [])

    Example:
        POST /tracks/0a1f/patterns
        Headers:
            X-Client-ID: alice
            X-Client-Token: <token>
        Body:
        {
            "pattern_name": "main",
            "active": true,
            "events": []
        }
    """
    client_id = await verify_auth(x_client_id, x_client_token, container)

    try:
        pattern = container.patterns.create(
            track_id=track_id,
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
    summary="Update pattern (hierarchical API)"
)
async def update_pattern_hierarchical(
    track_id: str,
    pattern_id: str,
    req: PatternUpdateRequest,
    x_client_id: Annotated[str, Header()],
    x_client_token: Annotated[str, Header()],
    container: SessionContainer = Depends(get_container),
):
    """
    Update pattern (hierarchical API).

    Request Body (all optional):
        track_id: Move pattern to different track
        active: Change演奏ON/OFF state
        archived: Soft delete/restore (true=archive, false=restore)
        events: Replace events

    Example:
        PATCH /tracks/0a1f/patterns/3e2b
        Body: {"active": false}
    """
    client_id = await verify_auth(x_client_id, x_client_token, container)

    # Check ownership
    pattern = container.patterns.get_by_id(pattern_id)
    if pattern is None:
        raise HTTPException(status_code=404, detail="Pattern not found")
    if pattern.client_id != client_id:
        raise HTTPException(status_code=403, detail="You don't own this pattern")

    # Update
    try:
        updated = container.patterns.update(
            pattern_id=pattern_id,
            track_id=req.track_id,
            active=req.active,
            archived=req.archived,
            events=req.events,
        )
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    "/tracks/{track_id}/patterns/{pattern_id}",
    status_code=204,
    summary="Delete pattern (hierarchical API)"
)
async def delete_pattern_hierarchical(
    track_id: str,
    pattern_id: str,
    x_client_id: Annotated[str, Header()],
    x_client_token: Annotated[str, Header()],
    container: SessionContainer = Depends(get_container),
):
    """
    Soft delete a pattern (hierarchical API).

    Example:
        DELETE /tracks/0a1f/patterns/3e2b
        Headers:
            X-Client-ID: alice
            X-Client-Token: <token>
    """
    client_id = await verify_auth(x_client_id, x_client_token, container)

    # Check ownership
    pattern = container.patterns.get_by_id(pattern_id)
    if pattern is None:
        raise HTTPException(status_code=404, detail="Pattern not found")
    if pattern.client_id != client_id:
        raise HTTPException(status_code=403, detail="You don't own this pattern")

    # Soft delete
    success = container.patterns.delete(pattern_id)
    if not success:
        raise HTTPException(status_code=404, detail="Pattern not found")
