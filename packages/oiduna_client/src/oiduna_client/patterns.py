"""Pattern management client for Oiduna API"""

from typing import Any, Dict, Optional, cast
import httpx
from oiduna_client.models import (
    PatternSubmitRequest,
    PatternSubmitResponse,
    PatternValidateResponse,
    ActivePatternsResponse,
)
from oiduna_client.exceptions import OidunaAPIError, ValidationError, TimeoutError as OidunaTimeoutError


class PatternClient:
    """Client for Oiduna pattern management endpoints"""

    def __init__(self, http_client: httpx.AsyncClient):
        """Initialize pattern client

        Args:
            http_client: Shared HTTP client instance
        """
        self._http = http_client

    async def submit(
        self,
        pattern: Dict[str, Any],
        validate_only: bool = False
    ) -> PatternSubmitResponse:
        """Submit a pattern for execution

        Args:
            pattern: Oiduna IR format pattern data
            validate_only: If True, only validate without executing

        Returns:
            PatternSubmitResponse: Submission result with track ID

        Raises:
            ValidationError: Pattern is invalid
            TimeoutError: Request timed out
            OidunaAPIError: API error occurred

        Example:
            >>> async with OidunaClient() as client:
            ...     pattern = {"version": "1.0", "type": "pattern", "tracks": [...]}
            ...     result = await client.patterns.submit(pattern)
            ...     print(f"Playing: {result.track_id}")
        """
        try:
            request = PatternSubmitRequest(
                pattern=pattern,
                validate_only=validate_only
            )
            response = await self._http.post(
                "/patterns/submit",
                json=request.model_dump()
            )
            response.raise_for_status()
            return PatternSubmitResponse(**response.json())

        except httpx.TimeoutException as e:
            raise OidunaTimeoutError(f"Request timed out: {e}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                detail = e.response.json().get("detail", str(e))
                raise ValidationError(f"Pattern validation failed: {detail}")
            raise OidunaAPIError(f"API error: {e}")
        except httpx.RequestError as e:
            raise OidunaAPIError(f"Connection error: {e}")

    async def validate(self, pattern: Dict[str, Any]) -> PatternValidateResponse:
        """Validate a pattern without executing it

        Args:
            pattern: Oiduna IR format pattern data

        Returns:
            PatternValidateResponse: Validation result with errors if any

        Raises:
            OidunaAPIError: API error occurred

        Example:
            >>> async with OidunaClient() as client:
            ...     pattern = {"version": "1.0", "type": "pattern", "tracks": [...]}
            ...     result = await client.patterns.validate(pattern)
            ...     if result.valid:
            ...         print("Pattern is valid!")
            ...     else:
            ...         print(f"Errors: {result.errors}")
        """
        try:
            request = PatternSubmitRequest(pattern=pattern)
            response = await self._http.post(
                "/patterns/validate",
                json=request.model_dump()
            )
            response.raise_for_status()
            return PatternValidateResponse(**response.json())

        except httpx.HTTPStatusError as e:
            raise OidunaAPIError(f"API error: {e}")
        except httpx.RequestError as e:
            raise OidunaAPIError(f"Connection error: {e}")

    async def get_active(self) -> ActivePatternsResponse:
        """Get currently active patterns

        Returns:
            ActivePatternsResponse: List of active patterns

        Raises:
            OidunaAPIError: API error occurred

        Example:
            >>> async with OidunaClient() as client:
            ...     active = await client.patterns.get_active()
            ...     print(f"Active patterns: {active.count}")
            ...     for pattern in active.patterns:
            ...         print(f"  - {pattern['track_id']}")
        """
        try:
            response = await self._http.get("/patterns/active")
            response.raise_for_status()
            return ActivePatternsResponse(**response.json())

        except httpx.HTTPStatusError as e:
            raise OidunaAPIError(f"API error: {e}")
        except httpx.RequestError as e:
            raise OidunaAPIError(f"Connection error: {e}")

    async def stop(self, track_id: Optional[str] = None) -> Dict[str, Any]:
        """Stop pattern playback

        Args:
            track_id: Track ID to stop (None = stop all)

        Returns:
            Dict: Stop operation result

        Raises:
            OidunaAPIError: API error occurred

        Example:
            >>> async with OidunaClient() as client:
            ...     # Stop all patterns
            ...     await client.patterns.stop()
            ...     # Stop specific pattern
            ...     await client.patterns.stop(track_id="pattern-1")
        """
        try:
            payload = {"track_id": track_id} if track_id else {}
            response = await self._http.post("/patterns/stop", json=payload)
            response.raise_for_status()
            return cast(Dict[str, Any], response.json())

        except httpx.HTTPStatusError as e:
            raise OidunaAPIError(f"API error: {e}")
        except httpx.RequestError as e:
            raise OidunaAPIError(f"Connection error: {e}")
