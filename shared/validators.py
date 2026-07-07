"""
shared/validators.py
--------------------
Input validation helpers for Lambda request bodies.
"""

from typing import Any, Dict, List, Tuple


class ValidationError(Exception):
    """Raised when request body is missing required fields."""

    def __init__(self, missing: List[str]):
        self.missing = missing
        super().__init__(f"Missing required fields: {missing}")


def require_fields(body: Dict[str, Any], fields: List[str]) -> None:
    """Assert that all required fields are present and non-empty in body.

    Args:
        body: Parsed request body dict.
        fields: List of required field names.

    Raises:
        ValidationError: If any required field is absent or blank.
    """
    missing = [f for f in fields if not body.get(f)]
    if missing:
        raise ValidationError(missing)


def parse_body(event: Dict[str, Any]) -> Tuple[Dict[str, Any], None]:
    """Safely parse the JSON body from an API Gateway event.

    Args:
        event: Raw API Gateway proxy event.

    Returns:
        Parsed dict. Returns empty dict if body is absent.

    Raises:
        ValueError: If the body is not valid JSON.
    """
    import json

    raw = event.get("body") or "{}"
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON body: {exc}") from exc
