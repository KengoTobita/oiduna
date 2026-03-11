"""
FastAPI authentication dependencies.

Provides dependency functions for:
- Client token verification
- Admin password verification
"""

from typing import Annotated
from fastapi import Header, HTTPException, Depends
from .config import AuthConfig, load_auth_config


# Singleton auth config
_auth_config: AuthConfig | None = None


def get_auth_config() -> AuthConfig:
    """
    Get authentication configuration (singleton).

    Returns:
        AuthConfig instance
    """
    global _auth_config
    if _auth_config is None:
        _auth_config = load_auth_config()
    return _auth_config


async def verify_client_token(
    x_client_id: Annotated[str, Header()],
    x_client_token: Annotated[str, Header()],
) -> str:
    """
    Verify client authentication token.

    This is a placeholder that will be integrated with SessionManager
    in the full implementation. For now, it validates the header format.

    Args:
        x_client_id: Client ID from X-Client-ID header
        x_client_token: Token from X-Client-Token header

    Returns:
        Verified client_id

    Raises:
        HTTPException: 401 if credentials are invalid

    Example:
        >>> # In FastAPI route:
        >>> @router.get("/protected")
        >>> async def protected_route(
        ...     client_id: str = Depends(verify_client_token)
        ... ):
        ...     return {"client_id": client_id}
    """
    # NOTE: This is a placeholder implementation.
    # Full implementation will check against SessionManager.session.clients

    if not x_client_id or not x_client_token:
        raise HTTPException(
            status_code=401,
            detail="Missing client credentials (X-Client-ID and X-Client-Token required)"
        )

    # Basic validation - full check will be done by SessionManager
    if len(x_client_token) != 36:  # UUID4 format check
        raise HTTPException(
            status_code=401,
            detail="Invalid token format"
        )

    return x_client_id


async def verify_admin_password(
    x_admin_password: Annotated[str, Header()],
    auth_config: AuthConfig = Depends(get_auth_config),
) -> None:
    """
    Verify admin password for privileged operations.

    Args:
        x_admin_password: Password from X-Admin-Password header
        auth_config: Auth configuration

    Raises:
        HTTPException: 403 if password is invalid

    Example:
        >>> # In FastAPI route:
        >>> @router.delete("/admin/clients/{client_id}")
        >>> async def delete_client(
        ...     client_id: str,
        ...     _: None = Depends(verify_admin_password)
        ... ):
        ...     # Admin-only operation
        ...     pass
    """
    if x_admin_password != auth_config.admin_password:
        raise HTTPException(
            status_code=403,
            detail="Invalid admin password"
        )
