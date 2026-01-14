"""
OAuth2 flow endpoints.

Provides:
- OAuth2 password flow endpoint
- Token refresh endpoint
- Token revocation endpoint
"""

from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field

from backend.logging_config import get_logger
from backend.security.jwt_auth import (
    Token,
    User,
    create_tokens_for_user,
    refresh_access_token,
    authenticate_user,
    get_user,
    verify_access_token,
    verify_refresh_token,
)

logger = get_logger(__name__)

# OAuth2 router
oauth2_router = APIRouter(prefix="/oauth2", tags=["OAuth2"])


# Request models
class TokenRefreshRequest(BaseModel):
    """Token refresh request."""
    refresh_token: str = Field(..., description="Refresh token")


class TokenRevokeRequest(BaseModel):
    """Token revoke request."""
    token: str = Field(..., description="Token to revoke")


class UserRegisterRequest(BaseModel):
    """User registration request."""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    email: Optional[str] = None
    scopes: list[str] = Field(default_factory=lambda: ["read", "write"])


class UserResponse(BaseModel):
    """User response."""
    user_id: str
    username: str
    email: Optional[str] = None
    scopes: list[str]
    disabled: bool = False


# =============================================================================
# OAuth2 Token Endpoint (Password Flow)
# =============================================================================


@oauth2_router.post("/token", response_model=Token)
async def oauth2_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
):
    """
    OAuth2 token endpoint (password flow).

    Get an access token by providing username and password.

    **Scopes:**
    - `read`: Read access to API resources
    - `write`: Write access to API resources
    - `admin`: Administrative access

    Example with curl:
    ```bash
    curl -X POST "http://localhost:8000/oauth2/token" \
      -H "Content-Type: application/x-www-form-urlencoded" \
      -d "username=admin&password=admin&scope=read write"
    ```

    Example with Python requests:
    ```python
    import requests

    response = requests.post(
        "http://localhost:8000/oauth2/token",
        data={
            "username": "admin",
            "password": "admin",
            "scope": "read write"
        }
    )
    token_data = response.json()
    access_token = token_data["access_token"]
    ```

    Args:
        form_data: OAuth2 password form data

    Returns:
        Token with access_token and refresh_token
    """
    # Authenticate user
    user = authenticate_user(form_data.username, form_data.password)

    if not user:
        logger.warning("oauth2_auth_failed", username=form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Parse scopes from form data
    scopes = form_data.scopes if form_data.scopes else user.scopes

    # Validate requested scopes against user's scopes
    valid_scopes = [s for s in scopes if s in user.scopes]
    if not valid_scopes:
        valid_scopes = ["read"]  # Default scope

    # Create tokens
    token = create_tokens_for_user(user.user_id, valid_scopes)

    logger.info(
        "oauth2_token_issued",
        user_id=user.user_id,
        scopes=valid_scopes,
    )

    return token


# =============================================================================
# Token Refresh Endpoint
# =============================================================================


@oauth2_router.post("/refresh", response_model=Token)
async def oauth2_refresh(request: TokenRefreshRequest):
    """
    Refresh an access token using a refresh token.

    Example:
    ```bash
    curl -X POST "http://localhost:8000/oauth2/refresh" \
      -H "Content-Type: application/json" \
      -d '{"refresh_token": "your-refresh-token"}'
    ```

    Args:
        request: Token refresh request with refresh_token

    Returns:
        New Token with fresh access_token and refresh_token
    """
    token = refresh_access_token(request.refresh_token)

    if not token:
        logger.warning("oauth2_refresh_failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.info("oauth2_token_refreshed")

    return token


# =============================================================================
# Token Introspection Endpoint
# =============================================================================


@oauth2_router.post("/introspect")
async def oauth2_introspect(request: TokenRevokeRequest):
    """
    Introspect a token to get its metadata.

    Returns information about whether the token is active and its scopes.

    Example:
    ```bash
    curl -X POST "http://localhost:8000/oauth2/introspect" \
      -H "Content-Type: application/json" \
      -d '{"token": "your-access-token"}'
    ```

    Args:
        request: Token introspection request

    Returns:
        Token metadata
    """
    # Try as access token first
    token_data = verify_access_token(request.token)

    if token_data:
        user = get_user(token_data.user_id)

        return {
            "active": True,
            "token_type": "access",
            "user_id": token_data.user_id,
            "scopes": token_data.scopes,
            "disabled": user.disabled if user else True,
        }

    # Try as refresh token
    user_id = verify_refresh_token(request.token)

    if user_id:
        user = get_user(user_id)

        return {
            "active": True,
            "token_type": "refresh",
            "user_id": user_id,
            "disabled": user.disabled if user else True,
        }

    # Token is invalid or expired
    return {
        "active": False,
    }


# =============================================================================
# User Registration Endpoint
# =============================================================================


@oauth2_router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(request: UserRegisterRequest):
    """
    Register a new user.

    In production, this would store the user in a database with proper password hashing.

    Example:
    ```bash
    curl -X POST "http://localhost:8000/oauth2/register" \
      -H "Content-Type: application/json" \
      -d '{
        "username": "newuser",
        "password": "securepassword",
        "email": "newuser@example.com",
        "scopes": ["read", "write"]
      }'
    ```

    Args:
        request: User registration data

    Returns:
        Created user data
    """
    # Check if user already exists
    from backend.security.jwt_auth import USERS_DB

    if request.username in USERS_DB:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )

    # Create user (in production, hash password with bcrypt)
    user = User(
        user_id=request.username,  # In production, generate a proper ID
        username=request.username,
        email=request.email,
        scopes=request.scopes,
        disabled=False,
    )

    # Store user (in production, save to database)
    USERS_DB[request.username] = user

    logger.info("user_registered", user_id=user.user_id)

    return UserResponse(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        scopes=user.scopes,
        disabled=user.disabled,
    )


# =============================================================================
# User Info Endpoint
# =============================================================================


@oauth2_router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    token: str = Depends(lambda: "Bearer"),  # OAuth2 scheme dependency
):
    """
    Get current user info from bearer token.

    Example:
    ```bash
    curl -X GET "http://localhost:8000/oauth2/me" \
      -H "Authorization: Bearer your-access-token"
    ```

    Args:
        token: OAuth2 bearer token

    Returns:
        Current user information
    """
    # Extract token from Authorization header
    # This is a simplified version - use proper OAuth2 scheme in production

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Use the authentication dependency in protected endpoints instead",
    )
