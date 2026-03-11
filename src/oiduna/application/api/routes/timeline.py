"""POST/GET/PATCH/DELETE /playback/schedule - Timeline scheduling endpoints"""

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field

from oiduna.application.api.dependencies import get_container
from oiduna.application.api.services.loop_service import LoopService, get_loop_service
from oiduna.domain.session import SessionContainer
from oiduna.domain.schedule import ScheduleEntry, LoopSchedule

logger = logging.getLogger(__name__)

router = APIRouter()


# ================================================================
# Request/Response Models
# ================================================================

class ScheduleEntryRequest(BaseModel):
    """Individual scheduled message for timeline API"""

    destination_id: str = Field(..., description="Destination ID (e.g., 'superdirt')")
    cycle: float = Field(..., description="Cycle position")
    step: int = Field(..., ge=0, le=255, description="Step number (0-255)")
    params: dict = Field(default_factory=dict, description="Generic parameters dict")


class CueChangeRequest(BaseModel):
    """Request body for POST /playback/schedule"""

    target_global_step: int = Field(..., gt=0, description="When to apply (global step)")
    messages: list[ScheduleEntryRequest] = Field(
        ...,
        description="Messages to schedule"
    )
    bpm: float = Field(default=120.0, gt=0, description="Beats per minute")
    pattern_length: float = Field(default=4.0, gt=0, description="Pattern length in cycles")
    description: str = Field(default="", max_length=200, description="User description")


class UpdateChangeRequest(BaseModel):
    """Request body for PATCH /playback/schedule/{id}"""

    target_global_step: Optional[int] = Field(None, gt=0, description="New target step")
    messages: Optional[list[ScheduleEntryRequest]] = Field(None, description="New messages")
    bpm: Optional[float] = Field(None, gt=0, description="New BPM")
    pattern_length: Optional[float] = Field(None, gt=0, description="New pattern length")
    description: Optional[str] = Field(None, max_length=200, description="New description")


class ChangeResponse(BaseModel):
    """Response for scheduled change"""

    change_id: str
    target_global_step: int
    client_id: str
    client_name: str
    description: str
    cued_at: float
    sequence_number: int
    message_count: int


class CueChangeResponse(BaseModel):
    """Response for POST /playback/schedule"""

    status: str
    change_id: str
    target_global_step: int
    current_global_step: int


class TimelineResponse(BaseModel):
    """Response for GET /playback/timeline"""

    current_global_step: int
    upcoming_changes: list[ChangeResponse]


# ================================================================
# Authentication Helper
# ================================================================

def get_authenticated_client(
    x_client_id: Annotated[str, Header()],
    x_client_token: Annotated[str, Header()],
    container: SessionContainer = Depends(get_container),
) -> tuple[str, str]:
    """
    Verify client authentication and return (client_id, client_name).

    Raises HTTPException if authentication fails.
    """
    # Verify client exists and token is valid
    client = container.session.clients.get(x_client_id)
    if client is None:
        raise HTTPException(status_code=401, detail="Invalid client_id")

    if client.token != x_client_token:
        raise HTTPException(status_code=401, detail="Invalid token")

    return x_client_id, client.name


# ================================================================
# Endpoints
# ================================================================

@router.post("/schedule", response_model=CueChangeResponse)
async def cue_change(
    request: CueChangeRequest,
    client_auth: tuple[str, str] = Depends(get_authenticated_client),
    container: SessionContainer = Depends(get_container),
    loop_service: LoopService = Depends(get_loop_service),
) -> CueChangeResponse:
    """
    Schedule a pattern change for a future global step.

    Authentication: Requires X-Client-ID and X-Client-Token headers.
    """
    client_id, client_name = client_auth

    # Get current global step from engine
    engine = loop_service.get_engine()
    current_global_step = engine.get_global_step()

    # Validate target is in the future
    if request.target_global_step <= current_global_step:
        raise HTTPException(
            status_code=400,
            detail=f"target_global_step ({request.target_global_step}) must be > current ({current_global_step})"
        )

    # Convert messages to ScheduleEntry objects
    messages = [
        ScheduleEntry(
            destination_id=msg.destination_id,
            cycle=msg.cycle,
            step=msg.step,
            params=msg.params,
        )
        for msg in request.messages
    ]

    # Create batch
    batch = LoopSchedule(
        messages=tuple(messages),
        bpm=request.bpm,
        pattern_length=request.pattern_length,
    )

    # Schedule the change
    success, msg, change_id = container.timeline.cue_change(
        batch=batch,
        target_global_step=request.target_global_step,
        client_id=client_id,
        client_name=client_name,
        description=request.description,
        current_global_step=current_global_step,
    )

    if not success:
        raise HTTPException(status_code=400, detail=msg)

    return CueChangeResponse(
        status="scheduled",
        change_id=change_id,
        target_global_step=request.target_global_step,
        current_global_step=current_global_step,
    )


@router.get("/timeline", response_model=TimelineResponse)
async def get_timeline(
    limit: int = 100,
    client_auth: tuple[str, str] = Depends(get_authenticated_client),
    container: SessionContainer = Depends(get_container),
    loop_service: LoopService = Depends(get_loop_service),
) -> TimelineResponse:
    """
    Get all upcoming scheduled changes.

    Authentication: Requires X-Client-ID and X-Client-Token headers.
    """
    # Get current global step
    engine = loop_service.get_engine()
    current_global_step = engine.get_global_step()

    # Get upcoming changes
    changes = container.timeline.get_all_upcoming(current_global_step, limit)

    # Convert to response format
    change_responses = [
        ChangeResponse(
            change_id=change.change_id,
            target_global_step=change.target_global_step,
            client_id=change.client_id,
            client_name=change.client_name,
            description=change.description,
            cued_at=change.cued_at,
            sequence_number=change.sequence_number,
            message_count=len(change.batch.messages),
        )
        for change in changes
    ]

    return TimelineResponse(
        current_global_step=current_global_step,
        upcoming_changes=change_responses,
    )


@router.get("/schedule/{change_id}", response_model=ChangeResponse)
async def get_change(
    change_id: str,
    client_auth: tuple[str, str] = Depends(get_authenticated_client),
    container: SessionContainer = Depends(get_container),
) -> ChangeResponse:
    """
    Get a specific scheduled change by ID.

    Authentication: Requires X-Client-ID and X-Client-Token headers.
    """
    change = container.timeline.get_change(change_id)

    if change is None:
        raise HTTPException(status_code=404, detail=f"Change {change_id} not found")

    return ChangeResponse(
        change_id=change.change_id,
        target_global_step=change.target_global_step,
        client_id=change.client_id,
        client_name=change.client_name,
        description=change.description,
        cued_at=change.cued_at,
        sequence_number=change.sequence_number,
        message_count=len(change.batch.messages),
    )


@router.patch("/schedule/{change_id}")
async def update_change(
    change_id: str,
    request: UpdateChangeRequest,
    client_auth: tuple[str, str] = Depends(get_authenticated_client),
    container: SessionContainer = Depends(get_container),
    loop_service: LoopService = Depends(get_loop_service),
) -> dict:
    """
    Update a scheduled change (only owner can update).

    Authentication: Requires X-Client-ID and X-Client-Token headers.
    """
    client_id, _ = client_auth

    # Get existing change
    old_change = container.timeline.get_change(change_id)
    if old_change is None:
        raise HTTPException(status_code=404, detail=f"Change {change_id} not found")

    # Get current global step
    engine = loop_service.get_engine()
    current_global_step = engine.get_global_step()

    # Build new batch (use old values if not provided)
    if request.messages is not None:
        messages = [
            ScheduleEntry(
                destination_id=msg.destination_id,
                cycle=msg.cycle,
                step=msg.step,
                params=msg.params,
            )
            for msg in request.messages
        ]
    else:
        messages = old_change.batch.messages

    new_batch = LoopSchedule(
        messages=tuple(messages),
        bpm=request.bpm if request.bpm is not None else old_change.batch.bpm,
        pattern_length=request.pattern_length if request.pattern_length is not None else old_change.batch.pattern_length,
    )

    # Update the change
    success, msg = container.timeline.update_change(
        change_id=change_id,
        new_batch=new_batch,
        new_target_global_step=request.target_global_step if request.target_global_step is not None else old_change.target_global_step,
        new_description=request.description if request.description is not None else old_change.description,
        client_id=client_id,
        current_global_step=current_global_step,
    )

    if not success:
        raise HTTPException(status_code=400, detail=msg)

    return {"status": "updated", "change_id": change_id}


@router.delete("/schedule/{change_id}")
async def cancel_change(
    change_id: str,
    client_auth: tuple[str, str] = Depends(get_authenticated_client),
    container: SessionContainer = Depends(get_container),
) -> dict:
    """
    Cancel a scheduled change (only owner can cancel).

    Authentication: Requires X-Client-ID and X-Client-Token headers.
    """
    client_id, _ = client_auth

    # Cancel the change
    success, msg = container.timeline.cancel_change(change_id, client_id)

    if not success:
        if "not found" in msg:
            raise HTTPException(status_code=404, detail=msg)
        else:
            raise HTTPException(status_code=403, detail=msg)

    return {"status": "cancelled", "change_id": change_id}
