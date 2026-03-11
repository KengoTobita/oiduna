"""
Authentication configuration loading.

Loads auth settings from config.yaml.
"""

import yaml
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Optional


class AuthConfig(BaseModel):
    """
    Authentication configuration.

    Attributes:
        admin_password: Password for admin endpoints
    """

    admin_password: str = Field(
        default="change_me_in_production",
        description="Admin password for privileged operations"
    )


def load_auth_config(config_path: Optional[Path] = None) -> AuthConfig:
    """
    Load authentication configuration from config.yaml.

    Args:
        config_path: Path to config.yaml (defaults to ./config.yaml)

    Returns:
        AuthConfig instance

    Example:
        >>> config = load_auth_config()
        >>> config.admin_password
        'change_me_in_production'
    """
    if config_path is None:
        config_path = Path("config.yaml")

    if not config_path.exists():
        # Return default config if file doesn't exist
        return AuthConfig()

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        auth_data = data.get("auth", {})
        return AuthConfig(**auth_data)
    except Exception as e:
        # Log warning and return default config
        import warnings
        warnings.warn(
            f"Failed to load auth config from {config_path}: {e}. Using defaults.",
            UserWarning
        )
        return AuthConfig()
