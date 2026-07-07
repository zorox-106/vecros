"""
lambdas/list_by_warehouse/handler.py
--------------------------------------
GET /warehouses/{warehouse_id}/inspections

Lists all inspections associated with a given warehouse, ordered by creation
time (newest first) via GSI-1.

Access pattern:
    GSI1  →  GSI1PK = WAREHOUSE#<id>  &  GSI1SK begins_with INSPECTION#
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from typing import Any, Dict

from shared import db, response


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Entry point for List Inspections by Warehouse Lambda.

    Path parameter:
        warehouse_id  (str, required)

    Returns:
        200 with list of inspections, or 4xx/5xx on error.
    """
    # --- Extract path parameter -------------------------------------------
    path_params = event.get("pathParameters") or {}
    warehouse_id: str = path_params.get("warehouse_id", "").strip()

    if not warehouse_id:
        return response.error("warehouse_id path parameter is required.", status=400)

    # --- Query GSI-1 -------------------------------------------------------
    try:
        items = db.query_gsi(
            gsi_name="GSI1",
            pk_attr="GSI1PK",
            pk_value=db.pk_warehouse(warehouse_id),
            sk_attr="GSI1SK",
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
            "warehouse_id": warehouse_id,
            "count": len(inspections),
            "inspections": inspections,
        }
    )
