"""
API aggregation for combining multiple service responses.

Provides:
- Parallel API calls
- Response aggregation
- Error handling for partial failures
- Result merging strategies
"""

import asyncio
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel

from backend.logging_config import get_logger

logger = get_logger(__name__)


class MergeStrategy(Enum):
    """Strategies for merging multiple responses."""
    APPEND = "append"  # Append all responses
    MERGE = "merge"  # Merge dictionaries
    FIRST = "first"  # Return first successful response
    ALL = "all"  # Return all responses as list


@dataclass
class APICall:
    """Configuration for a single API call."""
    name: str
    url: str
    method: str = "GET"
    headers: Dict[str, str] = field(default_factory=dict)
    params: Dict[str, Any] = field(default_factory=dict)
    body: Optional[Dict[str, Any]] = None
    timeout: float = 30.0
    required: bool = False  # If True, failure will cause overall failure


@dataclass
class AggregationResult:
    """Result of API aggregation."""
    success: bool
    results: Dict[str, Any] = field(default_factory=dict)
    errors: Dict[str, str] = field(default_factory=dict)
    partial: bool = False
    total_duration_ms: float = 0.0


class APIAggregator:
    """
    Aggregates responses from multiple API calls.

    Features:
    - Parallel API calls
    - Timeout handling
    - Partial failure handling
    - Response merging
    """

    def __init__(self):
        """Initialize API aggregator."""
        self._client: Optional[Any] = None  # HTTP client

    def _get_client(self) -> Any:
        """Get or create HTTP client."""
        if self._client is None:
            import httpx
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client

    async def call_api(self, api_call: APICall) -> tuple[str, Any]:
        """
        Make a single API call.

        Args:
            api_call: API call configuration

        Returns:
            Tuple of (name, response_data)
        """
        client = self._get_client()

        try:
            if api_call.method.upper() == "GET":
                response = await client.get(
                    api_call.url,
                    headers=api_call.headers,
                    params=api_call.params,
                    timeout=api_call.timeout,
                )
            elif api_call.method.upper() == "POST":
                response = await client.post(
                    api_call.url,
                    headers=api_call.headers,
                    params=api_call.params,
                    json=api_call.body,
                    timeout=api_call.timeout,
                )
            elif api_call.method.upper() == "PUT":
                response = await client.put(
                    api_call.url,
                    headers=api_call.headers,
                    params=api_call.params,
                    json=api_call.body,
                    timeout=api_call.timeout,
                )
            elif api_call.method.upper() == "DELETE":
                response = await client.delete(
                    api_call.url,
                    headers=api_call.headers,
                    params=api_call.params,
                    timeout=api_call.timeout,
                )
            else:
                raise ValueError(f"Unsupported method: {api_call.method}")

            response.raise_for_status()
            data = response.json()

            logger.info(
                "api_call_success",
                name=api_call.name,
                status_code=response.status_code,
            )

            return api_call.name, data

        except Exception as e:
            logger.error(
                "api_call_failed",
                name=api_call.name,
                error=str(e),
            )

            if api_call.required:
                raise

            return api_call.name, {"error": str(e)}

    async def aggregate(
        self,
        api_calls: List[APICall],
        merge_strategy: MergeStrategy = MergeStrategy.MERGE,
    ) -> AggregationResult:
        """
        Aggregate responses from multiple API calls.

        Args:
            api_calls: List of API calls to make
            merge_strategy: Strategy for merging responses

        Returns:
            AggregationResult with all responses
        """
        import time
        start_time = time.time()

        # Create tasks for all API calls
        tasks = [self.call_api(api_call) for api_call in api_calls]

        # Execute in parallel
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            logger.error("aggregation_failed", error=str(e))
            return AggregationResult(
                success=False,
                errors={"all": str(e)},
                total_duration_ms=(time.time() - start_time) * 1000,
            )

        # Process results
        result = AggregationResult(
            success=True,
            total_duration_ms=(time.time() - start_time) * 1000,
        )

        for item in results:
            if isinstance(item, Exception):
                result.errors[str(id(item))] = str(item)
                result.partial = True
            else:
                name, data = item
                if "error" in data:
                    result.errors[name] = data["error"]
                    result.partial = True
                else:
                    result.results[name] = data

        # Check if any required calls failed
        for api_call in api_calls:
            if api_call.required and api_call.name in result.errors:
                result.success = False
                break

        # Merge results based on strategy
        if merge_strategy == MergeStrategy.APPEND:
            merged = []
            for data in result.results.values():
                if isinstance(data, list):
                    merged.extend(data)
                elif isinstance(data, dict):
                    merged.append(data)
            result.results = {"merged": merged}

        elif merge_strategy == MergeStrategy.MERGE:
            merged = {}
            for data in result.results.values():
                if isinstance(data, dict):
                    merged.update(data)
            result.results = merged

        elif merge_strategy == MergeStrategy.FIRST:
            # Get first successful result
            for name, data in result.results.items():
                result.results = {name: data}
                break

        elif merge_strategy == MergeStrategy.ALL:
            # Keep all results as-is (already set)
            pass

        return result

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# Global aggregator
_aggregator: Optional[APIAggregator] = None


def get_aggregator() -> APIAggregator:
    """Get global API aggregator."""
    global _aggregator
    if _aggregator is None:
        _aggregator = APIAggregator()
    return _aggregator


async def aggregate_responses(
    api_calls: List[APICall],
    merge_strategy: MergeStrategy = MergeStrategy.MERGE,
) -> AggregationResult:
    """
    Aggregate responses from multiple API calls using the global aggregator.

    Args:
        api_calls: List of API calls to make
        merge_strategy: Strategy for merging responses

    Returns:
        AggregationResult with all responses
    """
    aggregator = get_aggregator()
    return await aggregator.aggregate(api_calls, merge_strategy)
