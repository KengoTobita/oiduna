"""Tests for EnvironmentRepository."""

import pytest
from oiduna.domain.models import Session, Environment
from oiduna.domain.session.repositories import EnvironmentRepository


class TestEnvironmentRepository:
    """Test EnvironmentRepository data access operations."""

    def test_get_environment(self, session: Session) -> None:
        """Test getting the environment object."""
        repo = EnvironmentRepository(session)
        env = repo.get_environment()

        assert isinstance(env, Environment)
        assert env.bpm == 120.0  # Default BPM

    def test_get_all(self, session: Session) -> None:
        """Test getting all environment settings as dict."""
        repo = EnvironmentRepository(session)
        all_settings = repo.get_all()

        assert isinstance(all_settings, dict)
        assert "bpm" in all_settings
        assert "metadata" in all_settings
        assert "position_update_interval" in all_settings

    def test_get_single_field(self, session: Session) -> None:
        """Test getting a single environment field."""
        repo = EnvironmentRepository(session)

        bpm = repo.get("bpm")
        assert bpm == 120.0

        metadata = repo.get("metadata")
        assert metadata == {}

    def test_set_bpm(self, session: Session) -> None:
        """Test setting BPM."""
        repo = EnvironmentRepository(session)

        repo.set("bpm", 140.0)
        assert repo.get("bpm") == 140.0
        assert session.environment.bpm == 140.0

    def test_set_metadata(self, session: Session) -> None:
        """Test setting metadata."""
        repo = EnvironmentRepository(session)

        metadata = {"key": "Am", "scale": "minor"}
        repo.set("metadata", metadata)

        retrieved = repo.get("metadata")
        assert retrieved == metadata
        assert session.environment.metadata == metadata

    def test_set_position_update_interval(self, session: Session) -> None:
        """Test setting position_update_interval."""
        repo = EnvironmentRepository(session)

        repo.set("position_update_interval", "bar")
        assert repo.get("position_update_interval") == "bar"
        assert session.environment.position_update_interval == "bar"

    def test_update_multiple_fields(self, session: Session) -> None:
        """Test updating multiple fields at once."""
        repo = EnvironmentRepository(session)

        params = {
            "bpm": 150.0,
            "metadata": {"key": "C", "scale": "major"},
        }
        repo.update(params)

        assert repo.get("bpm") == 150.0
        assert repo.get("metadata") == {"key": "C", "scale": "major"}

    def test_get_nonexistent_field(self, session: Session) -> None:
        """Test getting a nonexistent field returns None."""
        repo = EnvironmentRepository(session)
        result = repo.get("nonexistent_field")
        assert result is None
