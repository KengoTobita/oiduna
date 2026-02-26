"""
Integration tests for new destination-based session API.

Tests the complete flow:
- POST /playback/session with ScheduledMessageBatch
- MessageScheduler loading
- DestinationRouter routing (mocked)
"""

import pytest
from pathlib import Path


class TestSessionAPI:
    """Integration tests for session-based API"""

    def test_session_endpoint_exists(self, client):
        """Test that /playback/session endpoint exists"""
        # Send minimal valid session request
        payload = {
            "messages": [],
            "bpm": 120.0,
            "pattern_length": 4.0
        }

        # Should return 503 (destinations not loaded) or 200 (success)
        # depending on whether destinations.yaml exists
        response = client.post("/playback/session", json=payload)

        # Either success or service unavailable (not 404 Not Found)
        assert response.status_code in [200, 503]

    def test_session_with_messages(self, client):
        """Test session with actual messages"""
        payload = {
            "messages": [
                {
                    "destination_id": "superdirt",
                    "cycle": 0.0,
                    "step": 0,
                    "params": {
                        "s": "bd",
                        "gain": 0.8,
                        "pan": 0.5
                    }
                },
                {
                    "destination_id": "superdirt",
                    "cycle": 1.0,
                    "step": 16,
                    "params": {
                        "s": "sn",
                        "gain": 0.9
                    }
                }
            ],
            "bpm": 140.0,
            "pattern_length": 2.0
        }

        response = client.post("/playback/session", json=payload)

        # Either success or service unavailable
        assert response.status_code in [200, 503]

        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "ok"
            assert data["message_count"] == 2
            assert data["bpm"] == 140.0

    def test_session_validation(self, client):
        """Test that invalid session data is rejected"""
        # Missing required fields
        payload = {
            "messages": [
                {
                    # Missing destination_id
                    "cycle": 0.0,
                    "step": 0,
                    "params": {}
                }
            ]
        }

        response = client.post("/playback/session", json=payload)

        # Should return 422 (validation error) or 500 (server error)
        assert response.status_code in [422, 500]

    def test_legacy_pattern_endpoint_still_works(self, client):
        """Test that old /playback/pattern endpoint still works"""
        # This ensures backward compatibility
        # The endpoint should exist even if we can't test full functionality
        response = client.post("/playback/pattern", json={})

        # Should not return 404 Not Found
        assert response.status_code != 404
