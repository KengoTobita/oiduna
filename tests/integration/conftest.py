"""Integration test configuration"""

import pytest
import httpx


@pytest.fixture
def base_url():
    """Base URL for integration tests"""
    return "http://localhost:57122"


@pytest.fixture
async def async_client():
    """Async HTTP client for integration tests"""
    async with httpx.AsyncClient() as client:
        yield client
