"""Main Oiduna client (統合クライアント)"""

from typing import Optional
import httpx
from oiduna_client.patterns import PatternClient
from oiduna_client.synthdef import SynthDefClient
from oiduna_client.samples import SampleClient
from oiduna_client.health import HealthClient


class OidunaClient:
    """Unified client for Oiduna API

    This client provides access to all Oiduna API endpoints through
    specialized sub-clients. It manages the HTTP client lifecycle and
    can be used as an async context manager.

    Example:
        >>> async with OidunaClient() as client:
        ...     health = await client.health.check()
        ...     pattern = {"version": "1.0", "type": "pattern", "tracks": [...]}
        ...     result = await client.patterns.submit(pattern)
    """

    def __init__(
        self,
        base_url: str = "http://localhost:57122",
        timeout: float = 30.0,
        http_client: Optional[httpx.AsyncClient] = None
    ):
        """Initialize Oiduna client

        Args:
            base_url: Oiduna API base URL
            timeout: Default request timeout in seconds
            http_client: Optional pre-configured HTTP client
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

        # Create or use provided HTTP client
        if http_client is not None:
            self._http_client = http_client
            self._owns_http_client = False
        else:
            self._http_client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=timeout
            )
            self._owns_http_client = True

        # Initialize sub-clients
        self.patterns = PatternClient(self._http_client)
        self.synthdef = SynthDefClient(self._http_client)
        self.samples = SampleClient(self._http_client)
        self.health = HealthClient(self._http_client)

    async def __aenter__(self) -> "OidunaClient":
        """Enter async context manager"""
        return self

    async def __aexit__(self, *args: object) -> None:
        """Exit async context manager"""
        await self.close()

    async def close(self) -> None:
        """Close HTTP client if owned by this instance"""
        if self._owns_http_client:
            await self._http_client.aclose()
