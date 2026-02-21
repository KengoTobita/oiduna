"""Health check client for Oiduna API"""

import asyncio
from typing import Optional
import httpx
from oiduna_client.models import HealthResponse
from oiduna_client.exceptions import OidunaAPIError, TimeoutError as OidunaTimeoutError


class HealthClient:
    """Client for Oiduna health check endpoints"""

    def __init__(self, http_client: httpx.AsyncClient):
        """Initialize health client

        Args:
            http_client: Shared HTTP client instance
        """
        self._http = http_client

    async def check(self) -> HealthResponse:
        """Check Oiduna system health

        Returns:
            HealthResponse: Health status with component details

        Raises:
            OidunaAPIError: API error occurred

        Example:
            >>> async with OidunaClient() as client:
            ...     health = await client.health.check()
            ...     print(f"Status: {health.status}")
        """
        try:
            response = await self._http.get("/health")
            response.raise_for_status()
            return HealthResponse(**response.json())

        except httpx.HTTPStatusError as e:
            raise OidunaAPIError(f"API error: {e}")
        except httpx.RequestError as e:
            raise OidunaAPIError(f"Connection error: {e}")

    async def wait_ready(
        self,
        timeout: float = 30.0,
        interval: float = 1.0
    ) -> HealthResponse:
        """Wait for Oiduna to become ready

        Args:
            timeout: Maximum time to wait in seconds
            interval: Polling interval in seconds

        Returns:
            HealthResponse: Health status when ready

        Raises:
            TimeoutError: Timeout waiting for ready state
            OidunaAPIError: API error occurred

        Example:
            >>> async with OidunaClient() as client:
            ...     health = await client.health.wait_ready(timeout=60.0)
            ...     print("Oiduna is ready!")
        """
        start = asyncio.get_event_loop().time()

        while True:
            try:
                health = await self.check()
                if health.status == "ok":
                    return health
            except OidunaAPIError:
                pass

            elapsed = asyncio.get_event_loop().time() - start
            if elapsed >= timeout:
                raise OidunaTimeoutError(f"Timeout waiting for Oiduna to become ready ({timeout}s)")

            await asyncio.sleep(interval)
