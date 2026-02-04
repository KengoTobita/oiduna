"""Tests for /tracks/* endpoints"""

import pytest
from fastapi.testclient import TestClient


def test_list_tracks_empty(client: TestClient):
    """Test listing tracks when no session loaded"""
    response = client.get("/tracks")
    assert response.status_code == 200
    data = response.json()
    assert "tracks" in data
    assert isinstance(data["tracks"], list)


def test_mute_nonexistent_track(client: TestClient):
    """Test muting a track that doesn't exist"""
    response = client.post(
        "/tracks/nonexistent/mute",
        json={"muted": True},
    )
    # Returns 500 with error message (Phase 1 error handling)
    assert response.status_code == 500
    assert "not found" in response.json()["detail"]


def test_solo_nonexistent_track(client: TestClient):
    """Test soloing a track that doesn't exist"""
    response = client.post(
        "/tracks/nonexistent/solo",
        json={"solo": True},
    )
    # Returns 500 with error message (Phase 1 error handling)
    assert response.status_code == 500
    assert "not found" in response.json()["detail"]
