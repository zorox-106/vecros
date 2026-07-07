"""
lambdas/list_by_drone/handler.py
----------------------------------
GET /drones/{drone_id}/inspections

Lists all inspections performed by a specific drone, ordered by creation time
via GSI-2.

Access pattern:
    GSI2  →  GSI2PK = DRONE#<id>  &  GSI2SK begins_with INSPECTION#
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from typing import Any, Dict

from shared import db, response


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Entry point for List Inspections by Drone Lambda.

    Path parameter:
        drone_id  (str, required)

    Returns:
        200 with list of inspections, or 4xx/5xx on error.
    """
    # --- Extract path parameter -------------------------------------------
    path_params = event.get("pathParameters") or {}
    drone_id: str = path_params.get("drone_id", "").strip()

    if not drone_id:
        return response.error("drone_id path parameter is required.", status=400)

    # --- Query GSI-2 -------------------------------------------------------
    try:
        items = db.query_gsi(
            gsi_name="GSI2",
            pk_attr="GSI2PK",
            pk_value=db.pk_drone(drone_id),
            sk_attr="GSI2SK",
            sk_prefix="INSPECTION#",
        )
    except Exception as exc:
        return response.internal_error(exc)

    # --- Shape response -----------------------------------------------------
    inspections = [
        {
            "inspection_id": item.get("inspection_id"),
            "warehouse_id": item.get("warehouse_id"),
            "drone_id": item.get("drone_id"),
            "notes": item.get("notes", ""),
            "status": item.get("status"),
            "created_at": item.get("created_at"),
        }
        for item in items
    ]

    return response.success(
        {
            "drone_id": drone_id,
            "count": len(inspections),
            "inspections": inspections,
        }
    )
