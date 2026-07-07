"""
lambdas/list_images/handler.py
--------------------------------
GET /inspections/{inspection_id}/images

Returns all images recorded for a given inspection.

Access pattern:
    Primary table query:
        PK = INSPECTION#<inspection_id>
        SK begins_with IMAGE#

Each IMAGE item was created by the generate_presigned_url Lambda.
This handler also generates short-lived pre-signed GET URLs so the client
can view the images directly.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from typing import Any, Dict

from shared import db, response
from shared.s3 import generate_presigned_get_url


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Entry point for List Images Lambda.

    Path parameter:
        inspection_id  (str, required)

    Returns:
        200 with list of image metadata + pre-signed GET URLs, or error.
    """
    # --- Extract path parameter -------------------------------------------
    path_params = event.get("pathParameters") or {}
    inspection_id: str = path_params.get("inspection_id", "").strip()

    if not inspection_id:
        return response.error("inspection_id path parameter is required.", status=400)

    # --- Verify inspection exists ------------------------------------------
    try:
        existing = db.get_item(pk=db.pk_inspection(inspection_id), sk=db.SK_METADATA)
    except Exception as exc:
        return response.internal_error(exc)

    if not existing:
        return response.not_found("Inspection")

    # --- Query images for this inspection ---------------------------------
    try:
        items = db.query_by_pk(
            pk=db.pk_inspection(inspection_id),
            sk_prefix="IMAGE#",
        )
    except Exception as exc:
        return response.internal_error(exc)

    # --- Enrich with pre-signed GET URLs ----------------------------------
    expiry_seconds = int(os.environ.get("PRESIGNED_URL_EXPIRY_SECONDS", "3600"))
    images = []
    for item in items:
        s3_key = item.get("s3_key", "")
        try:
            view_url = generate_presigned_get_url(s3_key=s3_key, expiry=expiry_seconds)
        except Exception:
            view_url = None  # non-fatal — still return metadata

        images.append(
            {
                "image_id": item.get("image_id"),
                "inspection_id": item.get("inspection_id"),
                "file_name": item.get("file_name"),
                "content_type": item.get("content_type"),
                "s3_key": s3_key,
                "view_url": view_url,
                "created_at": item.get("created_at"),
            }
        )

    return response.success(
        {
            "inspection_id": inspection_id,
            "count": len(images),
            "images": images,
        }
    )
