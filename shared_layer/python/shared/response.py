"""
shared/response.py
------------------
Standard HTTP response builder for all Lambda handlers.
Ensures consistent JSON structure and proper CORS headers.
"""

import json
from typing import Any, Dict, Optional


def _build(status_code: int, body: Any) -> Dict:
    """Internal helper — builds the API Gateway proxy response dict."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
        },
        "body": json.dumps(body, default=str),  # default=str handles datetime / Decimal
    }


def success(data: Any, status: int = 200) -> Dict:
    """Return a successful API Gateway response.

    Args:
        data: The response payload (dict, list, etc.).
        status: HTTP status code (default 200).

    Returns:
        API Gateway proxy response dict.
    """
    return _build(status, data)


def created(data: Any) -> Dict:
    """Convenience wrapper for 201 Created responses."""
    return _build(201, data)


def error(message: str, status: int = 400, details: Optional[Any] = None) -> Dict:
    """Return an error API Gateway response.

    Args:
        message: Human-readable error message.
        status: HTTP status code (default 400).
        details: Optional extra context (validation errors, etc.).

    Returns:
        API Gateway proxy response dict.
    """
    body: Dict[str, Any] = {"error": message}
    if details is not None:
        body["details"] = details
    return _build(status, body)


def not_found(resource: str = "Resource") -> Dict:
    """Convenience wrapper for 404 Not Found responses."""
    return error(f"{resource} not found.", status=404)


def internal_error(exc: Optional[Exception] = None) -> Dict:
    """Convenience wrapper for 500 Internal Server Error responses."""
    msg = "An internal server error occurred."
    details = str(exc) if exc else None
    return error(msg, status=500, details=details)
