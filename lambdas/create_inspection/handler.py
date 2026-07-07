"""
lambdas/create_inspection/handler.py
-------------------------------------
POST /inspections

Creates a new inspection record associated with a warehouse and a drone.

DynamoDB writes:
  - PK=INSPECTION#<id>  SK=METADATA       (main record)
  - GSI1PK=WAREHOUSE#<id>  GSI1SK=INSPECTION#<ts>   (for list-by-warehouse)
  - GSI2PK=DRONE#<id>      GSI2SK=INSPECTION#<ts>   (for list-by-drone)
"""

import sys
import os

# Allow Lambda to resolve the shared package whether deployed or run locally
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from shared import db, response
from shared.validators import ValidationError, parse_body, require_fields


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Entry point for the Create Inspection Lambda.

    Expected JSON body:
        warehouse_id  (str, required)
        drone_id      (str, required)
        notes         (str, optional)
        status        (str, optional, default "CREATED")

    Returns:
        201 with the created inspection object, or 4xx/5xx on error.
    """
    # --- Parse & validate body -------------------------------------------
    try:
        body = parse_body(event)
    except ValueError as exc:
        return response.error(str(exc), status=400)

    try:
        require_fields(body, ["warehouse_id", "drone_id"])
    except ValidationError as exc:
        return response.error("Validation failed.", status=400, details=exc.missing)

    # --- Build entity -------------------------------------------------------
    inspection_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    warehouse_id: str = body["warehouse_id"]
    drone_id: str = body["drone_id"]
    status: str = body.get("status", "CREATED")
    notes: str = body.get("notes", "")

    item = {
        # Primary key
        "PK": db.pk_inspection(inspection_id),
        "SK": db.SK_METADATA,
        # GSI-1: query by warehouse
        "GSI1PK": db.pk_warehouse(warehouse_id),
        "GSI1SK": f"INSPECTION#{now}",
        # GSI-2: query by drone
        "GSI2PK": db.pk_drone(drone_id),
        "GSI2SK": f"INSPECTION#{now}",
        # Entity data
        "entity_type": "INSPECTION",
        "inspection_id": inspection_id,
        "warehouse_id": warehouse_id,
        "drone_id": drone_id,
        "notes": notes,
        "status": status,
        "created_at": now,
    }

    # --- Persist ------------------------------------------------------------
    try:
        db.put_item(item)
    except Exception as exc:
        return response.internal_error(exc)

    # --- Return created item ------------------------------------------------
    return response.created(
        {
            "inspection_id": inspection_id,
            "warehouse_id": warehouse_id,
            "drone_id": drone_id,
            "notes": notes,
            "status": status,
            "created_at": now,
        }
    )
