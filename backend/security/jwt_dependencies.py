"""
JWT authentication dependencies for FastAPI.

Provides:
- JWT bearer token scheme
- JWT authentication dependency
- Scope-based authorization
"""

from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from jwt.exceptions import InvalidTokenError

from backend.logging_config import get_logger
from backend.security.jwt_auth import (
    TokenData,
    verify_access_token,
    get_user,
)

logger = get_logger(__name__)

# OAuth2 scheme for JWT bearer tokens
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/oauth2/token",
    auto_error=False,
)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> TokenData:
    """
    Get current user from JWT bearer token.

    Use this dependency to protect endpoints with JWT authentication.

    Example:
    ```python
    @app.get("/protected")
    async def protected_endpoint(current_user: TokenData = Depends(get_current_user)):
        return {"user_id": current_user.user_id, "scopes": current_user.scopes}
    ```

    Args:
        token: JWT bearer token from Authorization header

    Returns:
        TokenData with user information

    Raises:
        HTTPException: If token is invalid or expired
    """
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = verify_access_token(token)

    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token_data


async def get_current_user_optional(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> Optional[TokenData]:
    """
    Get current user from JWT token (optional).

    Unlike get_current_user, this returns None instead of raising an exception
    if authentication fails. Useful for endpoints that work with or without auth.

    Args:
        token: JWT bearer token from Authorization header

    Returns:
        TokenData if valid, None otherwise
    """
    if token is None:
        return None

    return verify_access_token(token)


async def require_scope(
    *required_scopes: str,
):
    """
    Dependency factory to require specific scopes.

    Example:
    ```python
    @app.get("/admin")
    async def admin_endpoint(
        current_user: TokenData = Depends(get_current_user),
        _authorized: None = Depends(require_scope("admin")),
    ):
        return {"message": "Welcome admin!"}
    ```

    Args:
        *required_scopes: Required scope(s)

    Returns:
        Dependency function that validates scopes
    """
    async def scope_checker(
        current_user: Annotated[TokenData, Depends(get_current_user)],
    ) -> TokenData:
        """Check if user has required scopes."""
        user_scopes = set(current_user.scopes)
        required = set(required_scopes)

        if not required.intersection(user_scopes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required scope(s): {', '.join(required)}",
            )

        return current_user

    return scope_checker


async def get_current_active_user(
    current_user: Annotated[TokenData, Depends(get_current_user)],
) -> TokenData:
    """
    Get current active (non-disabled) user.

    Example:
    ```python
    @app.get("/profile")
    async def profile(
        current_user: TokenData = Depends(get_current_active_user),
    ):
        return {"user_id": current_user.user_id}
    ```

    Args:
        current_user: Current user from token

    Returns:
        TokenData if user is active

    Raises:
        HTTPException: If user is disabled
    """
    user = get_user(current_user.user_id)

    if user is None or user.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    return current_user


# Convenience dependencies for common scopes
require_admin = require_scope("admin")
require_write = require_scope("write")
require_read = require_scope("read")
