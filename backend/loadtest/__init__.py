"""
Load testing framework for performance testing.

Provides:
- Load test scenarios
- Concurrent request execution
- Performance metrics collection
- Result analysis
"""

import asyncio
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from enum import Enum

import httpx

from backend.logging_config import get_logger

logger = get_logger(__name__)


class LoadTestStatus(Enum):
    """Load test status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class LoadTestConfig:
    """Configuration for a load test."""
    name: str
    target_url: str
    method: str = "GET"
    headers: Dict[str, str] = field(default_factory=dict)
    body: Optional[str] = None
    params: Dict[str, str] = field(default_factory=dict)
    concurrent_users: int = 10
    requests_per_user: int = 10
    ramp_up_time: float = 0.0  # Seconds between starting each user
    timeout: float = 30.0


@dataclass
class RequestResult:
    """Result of a single request."""
    success: bool
    status_code: int
    response_time_ms: float
    error: Optional[str] = None
    user_id: int = 0
    request_number: int = 0


@dataclass
class LoadTestResult:
    """Results of a load test."""
    test_name: str
    status: LoadTestStatus
    start_time: float
    end_time: float = 0.0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time_ms: float = 0.0
    min_response_time_ms: float = 0.0
    max_response_time_ms: float = 0.0
    p50_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0
    p99_response_time_ms: float = 0.0
    requests_per_second: float = 0.0
    errors: List[str] = field(default_factory=list)
    results: List[RequestResult] = field(default_factory=list)


class LoadTestRunner:
    """
    Runs load tests against endpoints.

    Features:
    - Concurrent user simulation
    - Request rate limiting
    - Response time metrics
    - Error tracking
    """

    def __init__(self):
        """Initialize load test runner."""
        self._client: Optional[httpx.AsyncClient] = None

    async def run_test(self, config: LoadTestConfig) -> LoadTestResult:
        """
        Run a load test with the given configuration.

        Args:
            config: Load test configuration

        Returns:
            Load test results
        """
        start_time = time.time()
        result = LoadTestResult(
            test_name=config.name,
            status=LoadTestStatus.RUNNING,
            start_time=start_time,
        )

        logger.info(
            "load_test_started",
            test_name=config.name,
            concurrent_users=config.concurrent_users,
            requests_per_user=config.requests_per_user,
        )

        # Create HTTP client
        async with httpx.AsyncClient(timeout=config.timeout) as client:
            # Create tasks for each user
            user_tasks = []
            for user_id in range(config.concurrent_users):
                task = self._run_user_session(
                    config,
                    user_id,
                    client,
                )
                user_tasks.append(task)

                # Ramp up delay
                if config.ramp_up_time > 0:
                    await asyncio.sleep(config.ramp_up_time)

            # Execute all users concurrently
            user_results = await asyncio.gather(*user_tasks, return_exceptions=True)

            # Collect results
            for user_result in user_results:
                if isinstance(user_result, Exception):
                    logger.error("user_session_failed", error=str(user_result))
                    result.errors.append(str(user_result))
                elif isinstance(user_result, list):
                    result.results.extend(user_result)

        # Calculate metrics
        result.end_time = time.time()
        result.total_requests = len(result.results)

        successful = [r for r in result.results if r.success]
        failed = [r for r in result.results if not r.success]

        result.successful_requests = len(successful)
        result.failed_requests = len(failed)

        if successful:
            response_times = [r.response_time_ms for r in successful]
            result.avg_response_time_ms = statistics.mean(response_times)
            result.min_response_time_ms = min(response_times)
            result.max_response_time_ms = max(response_times)
            result.p50_response_time_ms = statistics.median(response_times)
            result.p95_response_time_ms = self._percentile(response_times, 95)
            result.p99_response_time_ms = self._percentile(response_times, 99)

        duration = result.end_time - result.start_time
        if duration > 0:
            result.requests_per_second = result.total_requests / duration

        result.status = LoadTestStatus.COMPLETED

        logger.info(
            "load_test_completed",
            test_name=config.name,
            total_requests=result.total_requests,
            successful_requests=result.successful_requests,
            failed_requests=result.failed_requests,
            avg_response_time_ms=result.avg_response_time_ms,
        )

        return result

    async def _run_user_session(
        self,
        config: LoadTestConfig,
        user_id: int,
        client: httpx.AsyncClient,
    ) -> List[RequestResult]:
        """
        Run a user session (multiple requests).

        Args:
            config: Load test configuration
            user_id: User identifier
            client: HTTP client

        Returns:
            List of request results
        """
        results = []

        for request_number in range(config.requests_per_user):
            start_time = time.time()

            try:
                if config.method.upper() == "GET":
                    response = await client.get(
                        config.target_url,
                        headers=config.headers,
                        params=config.params,
                    )
                elif config.method.upper() == "POST":
                    response = await client.post(
                        config.target_url,
                        headers=config.headers,
                        params=config.params,
                        content=config.body,
                    )
                elif config.method.upper() == "PUT":
                    response = await client.put(
                        config.target_url,
                        headers=config.headers,
                        params=config.params,
                        content=config.body,
                    )
                elif config.method.upper() == "DELETE":
                    response = await client.delete(
                        config.target_url,
                        headers=config.headers,
                        params=config.params,
                    )
                else:
                    raise ValueError(f"Unsupported method: {config.method}")

                response_time_ms = (time.time() - start_time) * 1000

                results.append(RequestResult(
                    success=True,
                    status_code=response.status_code,
                    response_time_ms=response_time_ms,
                    user_id=user_id,
                    request_number=request_number,
                ))

            except Exception as e:
                response_time_ms = (time.time() - start_time) * 1000

                results.append(RequestResult(
                    success=False,
                    status_code=0,
                    response_time_ms=response_time_ms,
                    error=str(e),
                    user_id=user_id,
                    request_number=request_number,
                ))

                logger.debug(
                    "request_failed",
                    test_name=config.name,
                    user_id=user_id,
                    request_number=request_number,
                    error=str(e),
                )

        return results

    def _percentile(self, data: List[float], p: int) -> float:
        """Calculate percentile of a list of values."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * p / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]


class LoadTestScenarios:
    """Predefined load test scenarios."""

    @staticmethod
    def simple_get(url: str, **kwargs) -> LoadTestConfig:
        """Simple GET request load test."""
        return LoadTestConfig(
            name="simple_get",
            target_url=url,
            method="GET",
            **kwargs,
        )

    @staticmethod
    def chat_compression(base_url: str, **kwargs) -> LoadTestConfig:
        """Chat endpoint load test."""
        import json

        return LoadTestConfig(
            name="chat_compression",
            target_url=f"{base_url}/chat",
            method="POST",
            headers={"Content-Type": "application/json"},
            body=json.dumps({
                "messages": [
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": "Hello"}],
                    }
                ]
            }),
            **kwargs,
        )


# Global runner
_runner: Optional[LoadTestRunner] = None


def get_runner() -> LoadTestRunner:
    """Get global load test runner."""
    global _runner
    if _runner is None:
        _runner = LoadTestRunner()
    return _runner


async def run_load_test(config: LoadTestConfig) -> LoadTestResult:
    """
    Run a load test using the global runner.

    Args:
        config: Load test configuration

    Returns:
        Load test results
    """
    runner = get_runner()
    return await runner.run_test(config)
