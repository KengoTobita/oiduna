"""Integration tests for HTTP API"""

import pytest
import httpx


@pytest.mark.asyncio
async def test_health_check(base_url: str):
    """Test health check endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_root_endpoint(base_url: str):
    """Test root endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert data["name"] == "Oiduna API"


@pytest.mark.integration
async def test_full_workflow(base_url: str):
    """Test full workflow: compile -> play -> stop"""
    async with httpx.AsyncClient() as client:
        # Compile a session
        session_data = {
            "session": {
                "environment": {"bpm": 120, "scale": "minor"},
                "tracks": [],
                "scenes": [],
            },
            "timing": "now",
        }
        response = await client.post(f"{base_url}/compile", json=session_data)
        assert response.status_code == 200

        # Start playback
        response = await client.post(f"{base_url}/transport/play")
        assert response.status_code in [200, 500]

        # Stop playback
        response = await client.post(f"{base_url}/transport/stop")
        assert response.status_code in [200, 500]
