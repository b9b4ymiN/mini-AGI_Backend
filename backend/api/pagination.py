"""
Pagination utilities for API endpoints.

Provides:
- Pagination parameters (page, page_size, cursor)
- Paginated response models
- Helper functions for paginated queries
"""

from typing import Generic, TypeVar, Optional, List, Any
from pydantic import BaseModel, Field, validator
from fastapi import Query, HTTPException

T = TypeVar("T")


class PaginationParams(BaseModel):
    """
    Pagination parameters for list endpoints.

    Supports both offset-based and cursor-based pagination.
    """

    page: int = Field(1, ge=1, description="Page number (starts at 1)")
    page_size: int = Field(20, ge=1, le=100, description="Items per page (max 100)")

    class Config:
        json_schema_extra = {
            "example": {
                "page": 1,
                "page_size": 20
            }
        }


class CursorPaginationParams(BaseModel):
    """
    Cursor-based pagination parameters.

    Uses cursors for efficient pagination through large datasets.
    """

    cursor: Optional[str] = Field(None, description="Cursor for next page")
    limit: int = Field(20, ge=1, le=100, description="Items per page (max 100)")

    class Config:
        json_schema_extra = {
            "example": {
                "cursor": "eyJpZCI6MTIzfQ==",
                "limit": 20
            }
        }


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Standard paginated response format.

    Generic type T represents the item type.
    """

    items: List[T] = Field(..., description="List of items for current page")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")

    class Config:
        json_schema_extra = {
            "example": {
                "items": [],
                "total": 100,
                "page": 1,
                "page_size": 20,
                "total_pages": 5,
                "has_next": True,
                "has_prev": False
            }
        }


class CursorPaginatedResponse(BaseModel, Generic[T]):
    """
    Cursor-based paginated response format.

    Provides cursors for navigating through the dataset.
    """

    items: List[T] = Field(..., description="List of items for current page")
    next_cursor: Optional[str] = Field(None, description="Cursor for next page")
    previous_cursor: Optional[str] = Field(None, description="Cursor for previous page")
    has_next: bool = Field(..., description="Whether there is a next page")
    limit: int = Field(..., description="Items per page")

    class Config:
        json_schema_extra = {
            "example": {
                "items": [],
                "next_cursor": "eyJpZCI6MTI0fQ==",
                "previous_cursor": None,
                "has_next": True,
                "limit": 20
            }
        }


def paginate(
    items: List[Any],
    total: int,
    params: PaginationParams
) -> PaginatedResponse:
    """
    Create a paginated response from a list of items.

    Args:
        items: List of items for current page
        total: Total number of items across all pages
        params: Pagination parameters

    Returns:
        PaginatedResponse with items and metadata
    """
    total_pages = (total + params.page_size - 1) // params.page_size
    has_next = params.page < total_pages
    has_prev = params.page > 1

    return PaginatedResponse(
        items=items,
        total=total,
        page=params.page,
        page_size=params.page_size,
        total_pages=total_pages,
        has_next=has_next,
        has_prev=has_prev
    )


def get_pagination_params(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page")
) -> PaginationParams:
    """
    Get pagination parameters from query string.

    Use as a FastAPI dependency:

        @app.get("/items")
        def list_items(pagination: PaginationParams = Depends(get_pagination_params)):
            ...

    Args:
        page: Page number (from query)
        page_size: Items per page (from query)

    Returns:
        PaginationParams object
    """
    return PaginationParams(page=page, page_size=page_size)


def calculate_offset(params: PaginationParams) -> int:
    """
    Calculate offset for database queries.

    Args:
        params: Pagination parameters

    Returns:
        Offset value (number of items to skip)
    """
    return (params.page - 1) * params.page_size


def calculate_limit(params: PaginationParams) -> int:
    """
    Get limit for database queries.

    Args:
        params: Pagination parameters

    Returns:
        Limit value (number of items to return)
    """
    return params.page_size


async def paginate_query(
    query,
    params: PaginationParams,
    count_query=None
) -> PaginatedResponse:
    """
    Paginate a SQLAlchemy query.

    Args:
        query: SQLAlchemy select query for items
        params: Pagination parameters
        count_query: Optional separate query for counting (for performance)

    Returns:
        PaginatedResponse with query results

    Example:
        result = await paginate_query(
            select(User).order_by(User.created_at),
            PaginationParams(page=1, page_size=20)
        )
    """
    from sqlalchemy import func, select
    from backend.database import get_session

    async with get_session() as session:
        # Get total count
        if count_query:
            total_result = await session.execute(count_query)
            total = total_result.scalar() or 0
        else:
            # Derive count from the query
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await session.execute(count_query)
            total = total_result.scalar() or 0

        # Apply pagination
        offset = calculate_offset(params)
        limit = calculate_limit(params)

        paginated_query = query.offset(offset).limit(limit)
        result = await session.execute(paginated_query)
        items = result.scalars().all()

        # Convert to dict for response
        items_list = [item.to_dict() if hasattr(item, "to_dict") else item for item in items]

    return paginate(items_list, total, params)
