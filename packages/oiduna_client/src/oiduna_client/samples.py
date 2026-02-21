"""Sample management client for Oiduna API"""

from typing import Optional
import httpx
from oiduna_client.models import SampleLoadRequest, SampleLoadResponse, BufferListResponse
from oiduna_client.exceptions import OidunaAPIError, TimeoutError as OidunaTimeoutError


class SampleClient:
    """Client for Oiduna sample management endpoints"""

    def __init__(self, http_client: httpx.AsyncClient):
        """Initialize sample client

        Args:
            http_client: Shared HTTP client instance
        """
        self._http = http_client

    async def load(
        self,
        category: str,
        path: str,
        timeout: Optional[float] = None
    ) -> SampleLoadResponse:
        """Load samples from a directory into SuperDirt

        Args:
            category: Sample category name (used in patterns as 's "category"')
            path: Absolute path to directory containing audio files
            timeout: Request timeout in seconds (overrides default)

        Returns:
            SampleLoadResponse: Load result with success status

        Raises:
            TimeoutError: SuperCollider confirmation timeout
            OidunaAPIError: API error occurred

        Example:
            >>> async with OidunaClient() as client:
            ...     result = await client.samples.load(
            ...         category="custom",
            ...         path="/path/to/samples/custom"
            ...     )
            ...     if result.loaded:
            ...         print(f"Loaded {result.category} samples!")
        """
        try:
            request = SampleLoadRequest(category=category, path=path)
            response = await self._http.post(
                "/superdirt/sample/load",
                json=request.model_dump(),
                timeout=timeout
            )
            response.raise_for_status()
            return SampleLoadResponse(**response.json())

        except httpx.TimeoutException as e:
            raise OidunaTimeoutError(f"Request timed out: {e}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 504:
                raise OidunaTimeoutError("SuperCollider confirmation timeout")
            raise OidunaAPIError(f"API error: {e}")
        except httpx.RequestError as e:
            raise OidunaAPIError(f"Connection error: {e}")

    async def list_buffers(self) -> BufferListResponse:
        """List all loaded sample buffers in SuperDirt

        Returns:
            BufferListResponse: List of buffer names and count

        Raises:
            OidunaAPIError: API error occurred

        Example:
            >>> async with OidunaClient() as client:
            ...     buffers = await client.samples.list_buffers()
            ...     print(f"Loaded buffers ({buffers.count}):")
            ...     for buffer in buffers.buffers:
            ...         print(f"  - {buffer}")
        """
        try:
            response = await self._http.get("/superdirt/buffers")
            response.raise_for_status()
            return BufferListResponse(**response.json())

        except httpx.HTTPStatusError as e:
            raise OidunaAPIError(f"API error: {e}")
        except httpx.RequestError as e:
            raise OidunaAPIError(f"Connection error: {e}")
