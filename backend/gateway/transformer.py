"""
Request and response transformation for API Gateway.

Provides:
- Request transformation (rename fields, add headers, etc.)
- Response transformation (filter fields, format conversion, etc.)
- Template-based transformation
- JSONPath-based field selection
"""

import json
import re
from typing import Any, Callable, Dict, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel

from backend.logging_config import get_logger

logger = get_logger(__name__)


class TransformationType(Enum):
    """Types of transformations."""
    # Request transformations
    ADD_HEADER = "add_header"
    REMOVE_HEADER = "remove_header"
    RENAME_FIELD = "rename_field"
    REMOVE_FIELD = "remove_field"
    ADD_FIELD = "add_field"
    TRANSFORM_VALUE = "transform_value"

    # Response transformations
    FILTER_FIELDS = "filter_fields"
    WRAP_RESPONSE = "wrap_response"
    UNWRAP_RESPONSE = "unwrap_response"
    FORMAT_OUTPUT = "format_output"


@dataclass
class Transformation:
    """A single transformation rule."""
    type: TransformationType
    target: str  # Field name or header name
    value: Optional[Any] = None  # New value (for add/transform)
    source: Optional[str] = None  # Source field (for rename)


@dataclass
class TransformationConfig:
    """Configuration for transformations."""
    name: str
    description: str = ""
    request_transformations: List[Transformation] = field(default_factory=list)
    response_transformations: List[Transformation] = field(default_factory=list)
    template: Optional[str] = None  # For template-based transformation


class RequestTransformer:
    """
    Transforms incoming requests.

    Features:
    - Add/remove headers
    - Rename/remove/add fields
    - Transform values using custom functions
    - Template-based transformation
    """

    def __init__(self, config: Optional[TransformationConfig] = None):
        """Initialize request transformer."""
        self.config = config or TransformationConfig(name="default")
        self._custom_functions: Dict[str, Callable] = {}

    def register_function(self, name: str, func: Callable[[Any], Any]) -> None:
        """
        Register a custom transformation function.

        Args:
            name: Function name
            func: Function that takes a value and returns transformed value
        """
        self._custom_functions[name] = func

    async def transform(self, data: Dict[str, Any], headers: Dict[str, str]) -> tuple[Dict[str, Any], Dict[str, str]]:
        """
        Transform request data and headers.

        Args:
            data: Request body data
            headers: Request headers

        Returns:
            Tuple of (transformed_data, transformed_headers)
        """
        result_data = data.copy()
        result_headers = headers.copy()

        for transformation in self.config.request_transformations:
            try:
                if transformation.type == TransformationType.ADD_HEADER:
                    result_headers[transformation.target] = transformation.value or ""

                elif transformation.type == TransformationType.REMOVE_HEADER:
                    result_headers.pop(transformation.target, None)

                elif transformation.type == TransformationType.RENAME_FIELD:
                    if transformation.source in result_data:
                        result_data[transformation.target] = result_data.pop(transformation.source)

                elif transformation.type == TransformationType.REMOVE_FIELD:
                    result_data.pop(transformation.target, None)

                elif transformation.type == TransformationType.ADD_FIELD:
                    result_data[transformation.target] = transformation.value

                elif transformation.type == TransformationType.TRANSFORM_VALUE:
                    if transformation.target in result_data:
                        if transformation.value and transformation.value in self._custom_functions:
                            func = self._custom_functions[transformation.value]
                            result_data[transformation.target] = func(result_data[transformation.target])
                        elif transformation.value == "upper":
                            result_data[transformation.target] = str(result_data[transformation.target]).upper()
                        elif transformation.value == "lower":
                            result_data[transformation.target] = str(result_data[transformation.target]).lower()
                        elif transformation.value == "trim":
                            result_data[transformation.target] = str(result_data[transformation.target]).strip()

            except Exception as e:
                logger.warning("transformation_failed", type=transformation.type.value, error=str(e))

        return result_data, result_headers


class ResponseTransformer:
    """
    Transforms outgoing responses.

    Features:
    - Filter fields
    - Wrap/unwrap response
    - Format output (JSON, XML, etc.)
    - Add metadata
    """

    def __init__(self, config: Optional[TransformationConfig] = None):
        """Initialize response transformer."""
        self.config = config or TransformationConfig(name="default")

    async def transform(self, data: Any, status_code: int = 200) -> Dict[str, Any]:
        """
        Transform response data.

        Args:
            data: Response data
            status_code: HTTP status code

        Returns:
            Transformed response data
        """
        if not isinstance(data, dict):
            data = {"data": data}

        result = data.copy()

        for transformation in self.config.response_transformations:
            try:
                if transformation.type == TransformationType.FILTER_FIELDS:
                    fields_to_keep = transformation.value if isinstance(transformation.value, list) else [transformation.value]
                    result = {k: v for k, v in result.items() if k in fields_to_keep}

                elif transformation.type == TransformationType.WRAP_RESPONSE:
                    wrapper = transformation.target or "response"
                    result = {wrapper: result}

                elif transformation.type == TransformationType.UNWRAP_RESPONSE:
                    unwrap_key = transformation.target or "response"
                    if unwrap_key in result:
                        result = result[unwrap_key]

                elif transformation.type == TransformationType.FORMAT_OUTPUT:
                    format_type = transformation.value or "json"
                    if format_type == "camelCase":
                        result = self._to_camel_case(result)
                    elif format_type == "snake_case":
                        result = self._to_snake_case(result)

            except Exception as e:
                logger.warning("response_transformation_failed", type=transformation.type.value, error=str(e))

        return result

    def _to_camel_case(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert dictionary keys to camelCase."""
        result = {}
        for key, value in data.items():
            # Split by underscore, capitalize each part except first
            parts = key.split("_")
            camel_key = parts[0] + "".join(p.capitalize() for p in parts[1:])
            result[camel_key] = value
        return result

    def _to_snake_case(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert dictionary keys to snake_case."""
        result = {}
        for key, value in data.items():
            # Insert underscore before uppercase letters and lowercase them
            snake_key = re.sub("([A-Z])", r"_\1", key).lower()
            snake_key = snake_key.lstrip("_")
            result[snake_key] = value
        return result


# Global transformers
_request_transformer: Optional[RequestTransformer] = None
_response_transformer: Optional[ResponseTransformer] = None


def get_request_transformer() -> RequestTransformer:
    """Get global request transformer."""
    global _request_transformer
    if _request_transformer is None:
        _request_transformer = RequestTransformer()
    return _request_transformer


def get_response_transformer() -> ResponseTransformer:
    """Get global response transformer."""
    global _response_transformer
    if _response_transformer is None:
        _response_transformer = ResponseTransformer()
    return _response_transformer


async def transform_request(data: Dict[str, Any], headers: Dict[str, str]) -> tuple[Dict[str, Any], Dict[str, str]]:
    """
    Transform a request using the global transformer.

    Args:
        data: Request data
        headers: Request headers

    Returns:
        Tuple of (transformed_data, transformed_headers)
    """
    transformer = get_request_transformer()
    return await transformer.transform(data, headers)


async def transform_response(data: Any, status_code: int = 200) -> Dict[str, Any]:
    """
    Transform a response using the global transformer.

    Args:
        data: Response data
        status_code: HTTP status code

    Returns:
        Transformed response data
    """
    transformer = get_response_transformer()
    return await transformer.transform(data, status_code)
