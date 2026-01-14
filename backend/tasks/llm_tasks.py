"""
Background LLM processing tasks.

Provides:
- Async LLM request processing
- Batch LLM processing
- Response generation
- Cache management
"""

import json
from typing import Any, Dict, List, Optional

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

from backend.logging_config import get_logger
from backend.orchestrator.llm_cached import get_llm, LLMManager
from backend.cache import get_cache

logger = get_logger(__name__)


@shared_task(
    name="backend.tasks.llm_tasks.process_llm_request_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="llm",
)
def process_llm_request_task(
    self,
    prompt: str,
    persona: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    use_cache: bool = True,
) -> Dict[str, Any]:
    """
    Process an LLM request asynchronously.

    Args:
        self: Celery task instance
        prompt: The input prompt for the LLM
        persona: Optional persona to use
        model: Model name (uses default if not specified)
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate
        use_cache: Whether to use response caching

    Returns:
        Dictionary with response data
    """
    task_id = self.request.id

    logger.info(
        "llm_task_started",
        task_id=task_id,
        persona=persona,
        model=model,
    )

    try:
        # Get LLM manager
        llm_manager: LLMManager = get_llm()

        # Build parameters
        params = {
            "prompt": prompt,
        }
        if persona:
            params["persona"] = persona
        if model:
            params["model"] = model
        if temperature is not None:
            params["temperature"] = temperature
        if max_tokens is not None:
            params["max_tokens"] = max_tokens
        params["use_cache"] = use_cache

        # Process the request
        response = llm_manager.generate_response(**params)

        result = {
            "task_id": task_id,
            "status": "completed",
            "response": response.get("response"),
            "model": response.get("model"),
            "tokens_used": response.get("tokens_used"),
            "cached": response.get("cached", False),
        }

        logger.info(
            "llm_task_completed",
            task_id=task_id,
            tokens_used=result["tokens_used"],
            cached=result["cached"],
        )

        return result

    except SoftTimeLimitExceeded:
        logger.error("llm_task_timeout", task_id=task_id)
        return {
            "task_id": task_id,
            "status": "timeout",
            "error": "Task exceeded time limit",
        }

    except Exception as e:
        logger.error(
            "llm_task_failed",
            task_id=task_id,
            error=str(e),
            error_type=type(e).__name__,
        )

        # Retry on failure
        try:
            raise self.retry(exc=e, countdown=60)
        except Exception:
            return {
                "task_id": task_id,
                "status": "failed",
                "error": str(e),
            }


@shared_task(
    name="backend.tasks.llm_tasks.process_batch_llm_task",
    bind=True,
    max_retries=2,
    queue="llm",
)
def process_batch_llm_task(
    self,
    requests: List[Dict[str, Any]],
    persona: Optional[str] = None,
    use_cache: bool = True,
) -> Dict[str, Any]:
    """
    Process multiple LLM requests in batch.

    Args:
        self: Celery task instance
        requests: List of request dictionaries with 'prompt' key
        persona: Optional persona to use for all requests
        use_cache: Whether to use response caching

    Returns:
        Dictionary with batch results
    """
    task_id = self.request.id

    logger.info(
        "batch_llm_task_started",
        task_id=task_id,
        request_count=len(requests),
        persona=persona,
    )

    results = []
    successful = 0
    failed = 0

    for i, request in enumerate(requests):
        try:
            prompt = request.get("prompt", "")
            if not prompt:
                results.append({
                    "index": i,
                    "status": "skipped",
                    "error": "No prompt provided",
                })
                failed += 1
                continue

            # Get LLM manager
            llm_manager: LLMManager = get_llm()

            params = {
                "prompt": prompt,
                "persona": persona or request.get("persona"),
                "model": request.get("model"),
                "temperature": request.get("temperature"),
                "max_tokens": request.get("max_tokens"),
                "use_cache": use_cache,
            }

            response = llm_manager.generate_response(**params)

            results.append({
                "index": i,
                "status": "completed",
                "response": response.get("response"),
                "model": response.get("model"),
                "tokens_used": response.get("tokens_used"),
                "cached": response.get("cached", False),
            })
            successful += 1

        except Exception as e:
            logger.warning(
                "batch_item_failed",
                task_id=task_id,
                index=i,
                error=str(e),
            )
            results.append({
                "index": i,
                "status": "failed",
                "error": str(e),
            })
            failed += 1

    logger.info(
        "batch_llm_task_completed",
        task_id=task_id,
        successful=successful,
        failed=failed,
    )

    return {
        "task_id": task_id,
        "status": "completed",
        "total": len(requests),
        "successful": successful,
        "failed": failed,
        "results": results,
    }


@shared_task(
    name="backend.tasks.llm_tasks.generate_response_task",
    bind=True,
    queue="llm",
)
def generate_response_task(
    self,
    prompt: str,
    instruction_path: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2000,
) -> str:
    """
    Generate a simple text response (returns string directly).

    Useful for quick async text generation where full result metadata isn't needed.

    Args:
        self: Celery task instance
        prompt: The input prompt
        instruction_path: Optional instruction file path
        model: Model name
        temperature: Sampling temperature
        max_tokens: Maximum tokens

    Returns:
        Generated response text
    """
    task_id = self.request.id

    try:
        llm_manager: LLMManager = get_llm()

        # Load instruction if provided
        if instruction_path:
            from pathlib import Path
            instruction_file = Path(instruction_path)
            if instruction_file.exists():
                instruction = instruction_file.read_text(encoding="utf-8")
                prompt = f"{instruction}\n\n{prompt}"

        response = llm_manager.generate_response(
            prompt=prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return response.get("response", "")

    except Exception as e:
        logger.error(
            "generate_response_failed",
            task_id=task_id,
            error=str(e),
        )
        raise


@shared_task(
    name="backend.tasks.llm_tasks.clear_llm_cache_task",
    queue="default",
)
def clear_llm_cache_task(pattern: Optional[str] = None) -> Dict[str, Any]:
    """
    Clear LLM response cache.

    Args:
        pattern: Optional cache key pattern to clear (clears all if not specified)

    Returns:
        Dictionary with cleanup results
    """
    logger.info("clear_cache_task_started", pattern=pattern)

    try:
        cache = get_cache()

        if pattern:
            # Clear keys matching pattern
            cleared = 0
            # Simple pattern matching (prefix-based)
            for key in cache._cache.keys():
                if key.startswith(pattern):
                    cache.delete(key)
                    cleared += 1

            logger.info("cache_pattern_cleared", pattern=pattern, count=cleared)
            return {"status": "success", "cleared": cleared, "pattern": pattern}
        else:
            # Clear all cache
            count = len(cache._cache)
            cache._cache.clear()

            logger.info("cache_cleared", count=count)
            return {"status": "success", "cleared": count}

    except Exception as e:
        logger.error("clear_cache_failed", error=str(e))
        return {"status": "error", "error": str(e)}
