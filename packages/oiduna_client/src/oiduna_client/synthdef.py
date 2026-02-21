"""SynthDef management client for Oiduna API"""

from typing import Optional
from pathlib import Path
import httpx
from oiduna_client.models import SynthDefLoadRequest, SynthDefLoadResponse
from oiduna_client.exceptions import OidunaAPIError, TimeoutError as OidunaTimeoutError


class SynthDefClient:
    """Client for Oiduna SynthDef management endpoints"""

    def __init__(self, http_client: httpx.AsyncClient):
        """Initialize SynthDef client

        Args:
            http_client: Shared HTTP client instance
        """
        self._http = http_client

    async def load(
        self,
        name: str,
        code: str,
        timeout: Optional[float] = None
    ) -> SynthDefLoadResponse:
        """Load a SynthDef into SuperCollider

        Args:
            name: SynthDef name (valid SuperCollider identifier)
            code: SuperCollider code defining the SynthDef
            timeout: Request timeout in seconds (overrides default)

        Returns:
            SynthDefLoadResponse: Load result with success status

        Raises:
            TimeoutError: SuperCollider confirmation timeout
            OidunaAPIError: API error occurred

        Example:
            >>> async with OidunaClient() as client:
            ...     code = 'SynthDef(\\\\acid, { |out=0| Out.ar(out, SinOsc.ar(440)) }).add;'
            ...     result = await client.synthdef.load("acid", code)
            ...     if result.loaded:
            ...         print(f"SynthDef '{result.name}' loaded!")
        """
        try:
            request = SynthDefLoadRequest(name=name, code=code)
            response = await self._http.post(
                "/superdirt/synthdef",
                json=request.model_dump(),
                timeout=timeout
            )
            response.raise_for_status()
            return SynthDefLoadResponse(**response.json())

        except httpx.TimeoutException as e:
            raise OidunaTimeoutError(f"Request timed out: {e}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 504:
                raise OidunaTimeoutError("SuperCollider confirmation timeout")
            raise OidunaAPIError(f"API error: {e}")
        except httpx.RequestError as e:
            raise OidunaAPIError(f"Connection error: {e}")

    async def load_from_file(
        self,
        file_path: str,
        name: Optional[str] = None,
        timeout: Optional[float] = None
    ) -> SynthDefLoadResponse:
        """Load a SynthDef from a .scd file

        Args:
            file_path: Path to .scd file containing SynthDef
            name: SynthDef name (auto-detected from filename if None)
            timeout: Request timeout in seconds (overrides default)

        Returns:
            SynthDefLoadResponse: Load result with success status

        Raises:
            FileNotFoundError: File does not exist
            TimeoutError: SuperCollider confirmation timeout
            OidunaAPIError: API error occurred

        Example:
            >>> async with OidunaClient() as client:
            ...     result = await client.synthdef.load_from_file("acid.scd")
            ...     if result.loaded:
            ...         print(f"SynthDef '{result.name}' loaded!")
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        code = path.read_text()

        # Auto-detect name from filename if not provided
        if name is None:
            name = path.stem

        return await self.load(name, code, timeout=timeout)
