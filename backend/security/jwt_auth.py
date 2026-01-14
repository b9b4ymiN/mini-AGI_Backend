"""
JWT (JSON Web Token) authentication support.

Provides:
- JWT token generation and validation
- OAuth2 password flow
- Token refresh mechanism
- User authentication with JWT
"""

import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import jwt
from pydantic import BaseModel

from backend.logging_config import get_logger

logger = get_logger(__name__)


# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", os.getenv("API_KEY_SECRET", "your-secret-key-change-in-production"))
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))


class TokenPayload(BaseModel):
    """JWT token payload."""
    sub: str  # Subject (user_id)
    exp: int  # Expiration time
    iat: int  # Issued at
    type: str = "access"  # Token type (access or refresh)
    scopes: list[str] = []  # OAuth2 scopes


class Token(BaseModel):
    """Token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    scopes: list[str] = []


class TokenData(BaseModel):
    """Token data for validation."""
    user_id: str
    token_type: str = "access"
    scopes: list[str] = []


class User(BaseModel):
    """User model for authentication."""
    user_id: str
    username: str
    email: Optional[str] = None
    scopes: list[str] = ["read", "write"]
    disabled: bool = False


# In-memory user storage (in production, use a database)
USERS_DB: Dict[str, User] = {
    "admin": User(
        user_id="admin",
        username="admin",
        email="admin@example.com",
        scopes=["read", "write", "admin"],
        disabled=False,
    ),
    "user": User(
        user_id="user",
        username="user",
        email="user@example.com",
        scopes=["read", "write"],
        disabled=False,
    ),
}


def create_access_token(user_id: str, scopes: list[str] = None) -> tuple[str, int]:
    """
    Create a JWT access token.

    Args:
        user_id: User identifier
        scopes: OAuth2 scopes/permissions

    Returns:
        Tuple of (token, expires_in_seconds)
    """
    if scopes is None:
        scopes = ["read", "write"]

    now = datetime.utcnow()
    expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": now,
        "type": "access",
        "scopes": scopes,
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    expires_in = int((expire - now).total_seconds())

    logger.info("access_token_created", user_id=user_id, expires_in=expires_in)

    return token, expires_in


def create_refresh_token(user_id: str) -> str:
    """
    Create a JWT refresh token.

    Args:
        user_id: User identifier

    Returns:
        Refresh token
    """
    now = datetime.utcnow()
    expire = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": now,
        "type": "refresh",
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    logger.info("refresh_token_created", user_id=user_id)

    return token


def decode_token(token: str) -> Optional[TokenPayload]:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token string

    Returns:
        TokenPayload if valid, None if invalid
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return TokenPayload(**payload)
    except jwt.ExpiredSignatureError:
        logger.warning("token_expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning("invalid_token", error=str(e))
        return None


def verify_access_token(token: str) -> Optional[TokenData]:
    """
    Verify an access token and return user data.

    Args:
        token: JWT access token

    Returns:
        TokenData if valid, None if invalid
    """
    payload = decode_token(token)

    if not payload:
        return None

    if payload.type != "access":
        logger.warning("invalid_token_type", expected="access", got=payload.type)
        return None

    # Check if user exists
    user = get_user(payload.sub)
    if not user:
        logger.warning("user_not_found", user_id=payload.sub)
        return None

    if user.disabled:
        logger.warning("user_disabled", user_id=payload.sub)
        return None

    return TokenData(
        user_id=payload.sub,
        token_type=payload.type,
        scopes=payload.scopes,
    )


def verify_refresh_token(token: str) -> Optional[str]:
    """
    Verify a refresh token and return user_id.

    Args:
        token: JWT refresh token

    Returns:
        user_id if valid, None if invalid
    """
    payload = decode_token(token)

    if not payload:
        return None

    if payload.type != "refresh":
        return None

    # Check if user exists
    user = get_user(payload.sub)
    if not user or user.disabled:
        return None

    return payload.sub


def get_user(user_id: str) -> Optional[User]:
    """
    Get a user by ID.

    Args:
        user_id: User identifier

    Returns:
        User if found, None otherwise
    """
    # First check by user_id
    for user in USERS_DB.values():
        if user.user_id == user_id:
            return user

    # Then check by username (for backwards compatibility)
    return USERS_DB.get(user_id)


def authenticate_user(username: str, password: str) -> Optional[User]:
    """
    Authenticate a user with username and password.

    In production, this would check against a database with hashed passwords.

    Args:
        username: Username
        password: Password

    Returns:
        User if authentication successful, None otherwise
    """
    user = get_user(username)

    if not user:
        return None

    if user.disabled:
        return None

    # Simple password check (in production, use bcrypt/argon2)
    # For demo purposes, password is same as username
    if password != username:
        return None

    logger.info("user_authenticated", user_id=user.user_id)

    return user


def create_tokens_for_user(user_id: str, scopes: list[str] = None) -> Token:
    """
    Create access and refresh tokens for a user.

    Args:
        user_id: User identifier
        scopes: OAuth2 scopes

    Returns:
        Token with access and refresh tokens
    """
    user = get_user(user_id)
    if not user:
        raise ValueError(f"User not found: {user_id}")

    if scopes is None:
        scopes = user.scopes

    access_token, expires_in = create_access_token(user_id, scopes)
    refresh_token = create_refresh_token(user_id)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=expires_in,
        scopes=scopes,
    )


def refresh_access_token(refresh_token: str) -> Optional[Token]:
    """
    Refresh an access token using a refresh token.

    Args:
        refresh_token: Valid refresh token

    Returns:
        New Token if refresh successful, None otherwise
    """
    user_id = verify_refresh_token(refresh_token)

    if not user_id:
        return None

    return create_tokens_for_user(user_id)
