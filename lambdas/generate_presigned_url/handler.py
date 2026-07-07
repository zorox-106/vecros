"""
lambdas/generate_presigned_url/handler.py
------------------------------------------
POST /inspections/{inspection_id}/images/upload

Generates a pre-signed S3 PUT URL so the client can upload an inspection
image DIRECTLY to S3. Lambda never touches the image bytes.

Flow:
  1. Validate inspection exists in DynamoDB
  2. Generate a unique image_id (UUID)
  3. Construct S3 key: inspections/<inspection_id>/<image_id>/<file_name>
  4. Record image metadata in DynamoDB (PK=INSPECTION#<id>, SK=IMAGE#<image_id>)
  5. Return pre-signed PUT URL + image_id to caller

The client then does:  PUT <upload_url> with the file bytes + Content-Type header.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from shared import db, response
from shared.s3 import build_s3_key, generate_presigned_put_url
from shared.validators import ValidationError, parse_body, require_fields


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Entry point for Generate Pre-signed URL Lambda.

    Path parameter:
        inspection_id  (str, required)

    Expected JSON body:
        file_name     (str, required)   e.g. "shelf_row_3.jpg"
        content_type  (str, required)   e.g. "image/jpeg"

    Returns:
        200 with { upload_url, image_id, s3_key, expires_in }, or error.
    """
    # --- Extract path parameter -------------------------------------------
    path_params = event.get("pathParameters") or {}
    inspection_id: str = path_params.get("inspection_id", "").strip()

    if not inspection_id:
        return response.error("inspection_id path parameter is required.", status=400)

    # --- Parse & validate body -------------------------------------------
    try:
        body = parse_body(event)
    except ValueError as exc:
        return response.error(str(exc), status=400)

    try:
        require_fields(body, ["file_name", "content_type"])
    except ValidationError as exc:
        return response.error("Validation failed.", status=400, details=exc.missing)

    file_name: str = body["file_name"]
    content_type: str = body["content_type"]

    # --- Verify inspection exists ------------------------------------------
    try:
        existing = db.get_item(pk=db.pk_inspection(inspection_id), sk=db.SK_METADATA)
    except Exception as exc:
        return response.internal_error(exc)

    if not existing:
        return response.not_found("Inspection")

    # --- Generate IDs & S3 key --------------------------------------------
    image_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    s3_key = build_s3_key(inspection_id, image_id, file_name)

    # --- Generate pre-signed PUT URL --------------------------------------
    expiry_seconds = int(os.environ.get("PRESIGNED_URL_EXPIRY_SECONDS", "3600"))
    try:
        upload_url = generate_presigned_put_url(
            s3_key=s3_key,
            content_type=content_type,
            expiry=expiry_seconds,
        )
    except Exception as exc:
        return response.internal_error(exc)

    # --- Persist image metadata to DynamoDB -------------------------------
    image_item = {
        "PK": db.pk_inspection(inspection_id),
        "SK": db.sk_image(image_id),
        "entity_type": "IMAGE",
        "image_id": image_id,
        "inspection_id": inspection_id,
        "file_name": file_name,
        "content_type": content_type,
        "s3_key": s3_key,
        "created_at": now,
    }

    try:
        db.put_item(image_item)
    except Exception as exc:
        return response.internal_error(exc)

    # --- Return URL to client ----------------------------------------------
    return response.success(
        {
            "image_id": image_id,
            "inspection_id": inspection_id,
            "upload_url": upload_url,
            "s3_key": s3_key,
            "file_name": file_name,
            "expires_in": expiry_seconds,
        }
    )
