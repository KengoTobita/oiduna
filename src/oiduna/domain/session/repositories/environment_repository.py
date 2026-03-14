"""Environment repository for session environment data access."""

from typing import Any
from oiduna.domain.models import Session, Environment
from .base import BaseRepository


class EnvironmentRepository(BaseRepository):
    """
    Repository for environment data access.

    Provides direct access to session.environment object.
    No validation or event emission - pure data access only.
    """

    def get_environment(self) -> Environment:
        """Get the environment object."""
        return self.session.environment

    def get_all(self) -> dict[str, Any]:
        """Get all environment settings as dict."""
        return self.session.environment.model_dump()

    def get(self, key: str) -> Any:
        """Get a single environment field."""
        return getattr(self.session.environment, key, None)

    def set(self, key: str, value: Any) -> None:
        """Set a single environment field."""
        setattr(self.session.environment, key, value)

    def update(self, params: dict[str, Any]) -> None:
        """Update multiple environment fields."""
        for key, value in params.items():
            setattr(self.session.environment, key, value)
