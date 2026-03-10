"""Root conftest.py - Setup Python path for tests"""

import sys
from pathlib import Path
import pytest

# Add packages to Python path
root_dir = Path(__file__).parent.parent
packages_dir = root_dir / "packages"

sys.path.insert(0, str(packages_dir))


@pytest.fixture
def auth_headers(client):
    """Create a client and return auth headers."""
    response = client.post(
        "/clients/alice_001",
        json={"client_name": "Alice"}
    )
    token = response.json()["token"]
    return {
        "X-Client-ID": "alice_001",
        "X-Client-Token": token
    }


@pytest.fixture
def auth_headers_with_track(client, auth_headers):
    """Create client and track, return auth headers with track_id."""
    response = client.post(
        "/tracks",
        headers=auth_headers,
        json={"track_name": "kick", "destination_id": "superdirt"}
    )
    # Extract server-generated track_id
    track_id = response.json()["track_id"]
    
    # Add track_id to headers dict for easy access in tests
    auth_headers["_track_id"] = track_id
    return auth_headers
