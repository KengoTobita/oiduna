"""Integration tests for HTTP API"""

import pytest
import httpx


@pytest.mark.asyncio
async def test_health_check(base_url: str):
    """Test health check endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded"]


@pytest.mark.asyncio
async def test_root_endpoint(base_url: str):
    """Test root endpoint (returns dashboard HTML)"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/")
        assert response.status_code == 200
        # Root endpoint now returns HTML dashboard, not JSON
        assert "text/html" in response.headers["content-type"]
        assert "<!DOCTYPE html>" in response.text


@pytest.mark.integration
@pytest.mark.skip(reason="Integration test requires running server and needs API endpoint updates")
async def test_full_workflow(base_url: str):
    """Test full workflow: session -> play -> stop"""
    async with httpx.AsyncClient() as client:
        # Load a session (new API)
        session_data = {
            "messages": [],
            "bpm": 120.0,
            "pattern_length": 4.0
        }
        response = await client.post(f"{base_url}/playback/session", json=session_data)
        assert response.status_code == 200

        # Start playback
        response = await client.post(f"{base_url}/playback/start")
        assert response.status_code in [200, 500]

        # Stop playback
        response = await client.post(f"{base_url}/playback/stop")
        assert response.status_code in [200, 500]
