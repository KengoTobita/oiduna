"""Pydantic models for Oiduna API requests and responses"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
import re


# ============================================================
# REQUEST MODELS
# ============================================================


class PatternSubmitRequest(BaseModel):
    """Request to submit a pattern"""
    pattern: Dict[str, Any] = Field(..., description="Oiduna IR pattern data")
    validate_only: bool = Field(default=False, description="Validate only, do not execute")


class SynthDefLoadRequest(BaseModel):
    """Request to load a SynthDef"""
    name: str = Field(..., description="SynthDef name (valid SuperCollider identifier)")
    code: str = Field(..., description="SuperCollider SynthDef code")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate SynthDef name is a valid SuperCollider identifier"""
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', v):
            raise ValueError(f"Invalid SynthDef name: {v}")
        return v


class SampleLoadRequest(BaseModel):
    """Request to load samples"""
    category: str = Field(..., description="Sample category name")
    path: str = Field(..., description="Directory path containing audio files")


# ============================================================
# RESPONSE MODELS
# ============================================================


class PatternSubmitResponse(BaseModel):
    """Response from pattern submission"""
    status: str
    track_id: Optional[str] = None
    message: Optional[str] = None


class PatternValidateResponse(BaseModel):
    """Response from pattern validation"""
    valid: bool
    errors: Optional[List[str]] = None


class ActivePatternsResponse(BaseModel):
    """Response containing active patterns"""
    status: str
    patterns: List[Dict[str, Any]]
    count: int


class SynthDefLoadResponse(BaseModel):
    """Response from SynthDef load"""
    loaded: bool
    name: str
    message: Optional[str] = None


class SampleLoadResponse(BaseModel):
    """Response from sample load"""
    loaded: bool
    category: str
    message: Optional[str] = None


class BufferListResponse(BaseModel):
    """Response containing buffer list"""
    buffers: List[str]
    count: int


class HealthResponse(BaseModel):
    """Response from health check"""
    status: str
    version: str
    components: Dict[str, Any]
