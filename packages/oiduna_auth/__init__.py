"""
Authentication package for Oiduna.

Provides:
- Token generation and validation
- Auth configuration loading
- FastAPI dependencies for auth checks
"""

from .token import generate_token, validate_token
from .config import AuthConfig, load_auth_config
from .dependencies import verify_client_token, verify_admin_password, get_auth_config

__all__ = [
    "generate_token",
    "validate_token",
    "AuthConfig",
    "load_auth_config",
    "verify_client_token",
    "verify_admin_password",
    "get_auth_config",
]
