"""
Admin routes for privileged operations.

Requires X-Admin-Password header for all endpoints.
"""

from typing import Annotated, Any
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from oiduna_api.dependencies import get_session_manager
from oiduna_auth import verify_admin_password
from oiduna_session import SessionManager, SessionValidator
from oiduna_destination.destination_models import DestinationConfig, OscDestinationConfig, MidiDestinationConfig


router = APIRouter()


# Request/Response models
class DestinationResponse(BaseModel):
    """Response with destination info."""
    destinations: dict[str, Any]


class ClientDeleteResponse(BaseModel):
    """Response after deleting a client."""
    deleted: bool
    resources_deleted: dict[str, int]


class SessionResetResponse(BaseModel):
    """Response after resetting session."""
    message: str
    previous_counts: dict[str, int]


# Routes
@router.get(
    "/admin/destinations",
    response_model=DestinationResponse,
    summary="List all destinations"
)
async def list_destinations(
    _: None = Depends(verify_admin_password),
    manager: SessionManager = Depends(get_session_manager),
):
    """
    List all configured destinations.

    Requires admin password.

    Example:
        GET /admin/destinations
        Headers:
            X-Admin-Password: <password>
    """
    return DestinationResponse(destinations=manager.session.destinations)


@router.post(
    "/admin/destinations",
    status_code=201,
    summary="Add a new destination"
)
async def add_destination(
    destination: OscDestinationConfig | MidiDestinationConfig,
    _: None = Depends(verify_admin_password),
    manager: SessionManager = Depends(get_session_manager),
):
    """
    Add a new destination to the session.

    Requires admin password.

    Example:
        POST /admin/destinations
        Headers:
            X-Admin-Password: <password>
        Body:
        {
            "id": "superdirt",
            "type": "osc",
            "host": "127.0.0.1",
            "port": 57120,
            "address": "/dirt/play"
        }
    """
    try:
        manager.add_destination(destination)
        return {"message": "Destination added", "destination_id": destination.id}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.delete(
    "/admin/destinations/{destination_id}",
    status_code=204,
    summary="Remove a destination"
)
async def remove_destination(
    destination_id: str,
    force: bool = False,
    _: None = Depends(verify_admin_password),
    manager: SessionManager = Depends(get_session_manager),
):
    """
    Remove a destination from the session.

    If force=false (default), fails if tracks are using this destination.
    If force=true, removes destination even if in use.

    Requires admin password.

    Example:
        DELETE /admin/destinations/superdirt?force=true
        Headers:
            X-Admin-Password: <password>
    """
    # Check if destination is in use
    validator = SessionValidator()
    tracks_using = validator.check_destination_in_use(manager.session, destination_id)

    if tracks_using and not force:
        raise HTTPException(
            status_code=409,
            detail=f"Destination in use by tracks: {tracks_using}. Use ?force=true to remove anyway."
        )

    success = manager.remove_destination(destination_id)
    if not success:
        raise HTTPException(status_code=404, detail="Destination not found")


@router.delete(
    "/admin/clients/{client_id}",
    response_model=ClientDeleteResponse,
    summary="Force disconnect a client"
)
async def force_delete_client(
    client_id: str,
    cascade: bool = True,
    _: None = Depends(verify_admin_password),
    manager: SessionManager = Depends(get_session_manager),
):
    """
    Force disconnect a client (admin operation).

    If cascade=true (default), also deletes all tracks/patterns owned by client.
    If cascade=false, only removes the client entry.

    Requires admin password.

    Example:
        DELETE /admin/clients/alice_001?cascade=true
        Headers:
            X-Admin-Password: <password>
    """
    # Get client info before deleting
    client = manager.get_client(client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")

    # Delete resources if cascade
    resources_deleted = {"tracks": 0, "patterns": 0}
    if cascade:
        resources_deleted = manager.delete_client_resources(client_id)

    # Delete client
    success = manager.delete_client(client_id)

    return ClientDeleteResponse(
        deleted=success,
        resources_deleted=resources_deleted,
    )


@router.delete(
    "/admin/tracks/{track_id}",
    status_code=204,
    summary="Force delete a track"
)
async def force_delete_track(
    track_id: str,
    _: None = Depends(verify_admin_password),
    manager: SessionManager = Depends(get_session_manager),
):
    """
    Force delete a track (admin operation).

    Bypasses ownership checks.

    Requires admin password.

    Example:
        DELETE /admin/tracks/track_001
        Headers:
            X-Admin-Password: <password>
    """
    success = manager.delete_track(track_id)
    if not success:
        raise HTTPException(status_code=404, detail="Track not found")


@router.post(
    "/admin/session/reset",
    response_model=SessionResetResponse,
    summary="Reset entire session"
)
async def reset_session(
    _: None = Depends(verify_admin_password),
    manager: SessionManager = Depends(get_session_manager),
):
    """
    Reset the entire session to empty state.

    Deletes all:
    - Clients
    - Tracks
    - Patterns
    - Destinations

    Resets environment to defaults.

    Requires admin password.

    Example:
        POST /admin/session/reset
        Headers:
            X-Admin-Password: <password>
    """
    # Get counts before reset
    previous_counts = {
        "clients": len(manager.session.clients),
        "tracks": len(manager.session.tracks),
        "destinations": len(manager.session.destinations),
    }

    # Reset session
    manager.reset()

    return SessionResetResponse(
        message="Session reset complete",
        previous_counts=previous_counts,
    )
