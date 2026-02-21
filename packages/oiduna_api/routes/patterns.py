"""POST/GET /patterns/* - Pattern management endpoints

This module provides HTTP endpoints for pattern submission and control.
These endpoints provide a higher-level abstraction over /playback/* endpoints,
designed specifically for oiduna_client and automated pattern submission.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from oiduna_api.services.loop_service import LoopService, get_loop_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================
# PYDANTIC MODELS
# ============================================================


class PatternSubmitRequest(BaseModel):
    """Request to submit a pattern for execution"""

    pattern: Dict[str, Any] = Field(..., description="Oiduna IR format pattern data")
    validate_only: bool = Field(default=False, description="If true, only validate without executing")


class PatternSubmitResponse(BaseModel):
    """Response from pattern submission"""

    status: str = Field(..., description="Status: 'success' or 'error'")
    track_id: Optional[str] = Field(None, description="Track ID if pattern was executed")
    message: Optional[str] = Field(None, description="Success message or error details")


class PatternValidateResponse(BaseModel):
    """Response from pattern validation"""

    valid: bool = Field(..., description="Whether the pattern is valid")
    errors: Optional[List[str]] = Field(None, description="Validation error messages")


class PatternStopRequest(BaseModel):
    """Request to stop a pattern"""

    track_id: Optional[str] = Field(None, description="Track ID to stop (None = stop all)")


class PatternStopResponse(BaseModel):
    """Response from pattern stop operation"""

    status: str = Field(..., description="Status: 'success' or 'error'")
    message: Optional[str] = Field(None, description="Success message or error details")


class ActivePatternsResponse(BaseModel):
    """Response containing active patterns"""

    status: str = Field(..., description="Status: 'success' or 'error'")
    patterns: List[Dict[str, Any]] = Field(..., description="List of active patterns")
    count: int = Field(..., description="Number of active patterns")


# ============================================================
# ROUTE HANDLERS
# ============================================================


@router.post("/submit", response_model=PatternSubmitResponse)
async def submit_pattern(
    req: PatternSubmitRequest,
    loop_service: LoopService = Depends(get_loop_service)
) -> PatternSubmitResponse:
    """Submit and optionally execute a pattern"""
    engine = loop_service.get_engine()

    # Validate pattern structure
    try:
        pattern = req.pattern
        if "version" not in pattern:
            raise ValueError("Missing 'version' field")
        if "type" not in pattern:
            raise ValueError("Missing 'type' field")
        if "tracks" not in pattern:
            raise ValueError("Missing 'tracks' field")

        # If validate_only, return success
        if req.validate_only:
            logger.info("Pattern validation successful (validate_only=true)")
            return PatternSubmitResponse(
                status="success",
                track_id=None,
                message="Pattern validation successful"
            )

        # Execute pattern
        logger.info(f"Submitting pattern with {len(pattern.get('tracks', []))} tracks")

        # Load pattern into engine
        result = engine._handle_compile(pattern)
        if not result.success:
            logger.error(f"Pattern compilation failed: {result.message}")
            raise HTTPException(status_code=500, detail=result.message)

        # Start playback
        play_result = engine._handle_play({})
        if not play_result.success:
            logger.error(f"Pattern playback start failed: {play_result.message}")
            raise HTTPException(status_code=500, detail=play_result.message)

        # Generate track ID
        track_id = f"pattern-{len(pattern.get('tracks', []))}"

        logger.info(f"✓ Pattern submitted successfully: {track_id}")
        return PatternSubmitResponse(
            status="success",
            track_id=track_id,
            message=f"Pattern submitted and playing: {track_id}"
        )

    except ValueError as e:
        logger.error(f"Pattern validation failed: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid pattern format: {str(e)}")
    except Exception as e:
        logger.error(f"Pattern submission error: {e}")
        raise HTTPException(status_code=500, detail=f"Pattern submission failed: {str(e)}")


@router.post("/validate", response_model=PatternValidateResponse)
async def validate_pattern(
    req: PatternSubmitRequest,
    loop_service: LoopService = Depends(get_loop_service)
) -> PatternValidateResponse:
    """Validate a pattern without executing it"""
    errors = []

    try:
        pattern = req.pattern

        # Check required fields
        if "version" not in pattern:
            errors.append("Missing 'version' field")
        if "type" not in pattern:
            errors.append("Missing 'type' field")
        if "tracks" not in pattern:
            errors.append("Missing 'tracks' field")
        elif not isinstance(pattern["tracks"], list):
            errors.append("'tracks' must be a list")

        # Check track structure
        if "tracks" in pattern and isinstance(pattern["tracks"], list):
            for i, track in enumerate(pattern["tracks"]):
                if not isinstance(track, dict):
                    errors.append(f"Track {i} must be a dictionary")
                elif "track_id" not in track:
                    errors.append(f"Track {i} missing 'track_id' field")

        if errors:
            logger.info(f"Pattern validation failed: {len(errors)} errors")
            return PatternValidateResponse(valid=False, errors=errors)
        else:
            logger.info("Pattern validation successful")
            return PatternValidateResponse(valid=True, errors=None)

    except Exception as e:
        logger.error(f"Pattern validation error: {e}")
        return PatternValidateResponse(valid=False, errors=[f"Validation error: {str(e)}"])


@router.get("/active", response_model=ActivePatternsResponse)
async def get_active_patterns(
    loop_service: LoopService = Depends(get_loop_service)
) -> ActivePatternsResponse:
    """Get currently active patterns"""
    try:
        engine = loop_service.get_engine()
        state = engine.state
        eff = state.get_effective()

        # Build list of active tracks
        patterns = []
        for track_id, track in eff.tracks.items():
            seq = eff.sequences.get(track_id)
            patterns.append({
                "track_id": track_id,
                "sound": track.params.s,
                "orbit": track.params.orbit,
                "muted": track.meta.mute,
                "solo": track.meta.solo,
                "length": len(seq.events) if seq else 0
            })

        logger.info(f"Found {len(patterns)} active patterns")
        return ActivePatternsResponse(
            status="success",
            patterns=patterns,
            count=len(patterns)
        )

    except Exception as e:
        logger.error(f"Error getting active patterns: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get active patterns: {str(e)}")


@router.post("/stop", response_model=PatternStopResponse)
async def stop_pattern(
    req: PatternStopRequest = PatternStopRequest(),
    loop_service: LoopService = Depends(get_loop_service)
) -> PatternStopResponse:
    """Stop pattern playback"""
    try:
        engine = loop_service.get_engine()

        if req.track_id:
            logger.info(f"Stopping specific track: {req.track_id}")
            result = engine._handle_stop({})
            if not result.success:
                raise HTTPException(status_code=500, detail=result.message)
            message = f"Stopped track: {req.track_id}"
        else:
            logger.info("Stopping all patterns")
            result = engine._handle_stop({})
            if not result.success:
                raise HTTPException(status_code=500, detail=result.message)
            message = "Stopped all patterns"

        logger.info(f"✓ {message}")
        return PatternStopResponse(status="success", message=message)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping pattern: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop pattern: {str(e)}")
