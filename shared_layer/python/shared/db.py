"""
shared/db.py
------------
DynamoDB client and query helpers for the Drone Inspection service.

Single-table design:
    Table name    : DroneInspectionTable  (from env var TABLE_NAME)
    Primary key   : PK (partition) + SK (sort)
    GSI-1         : GSI1PK + GSI1SK  →  list inspections by warehouse / drones by warehouse
    GSI-2         : GSI2PK + GSI2SK  →  list inspections by drone
"""

import os
from typing import Any, Dict, List, Optional

import boto3
from boto3.dynamodb.conditions import Key

# ---------------------------------------------------------------------------
# Client initialisation — picks up Lambda execution role automatically
# ---------------------------------------------------------------------------

_TABLE_NAME: str = os.environ["TABLE_NAME"]

_dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "ap-south-1"))
_table = _dynamodb.Table(_TABLE_NAME)

# ---------------------------------------------------------------------------
# Key builders — centralised so every handler speaks the same language
# ---------------------------------------------------------------------------


def pk_warehouse(warehouse_id: str) -> str:
    return f"WAREHOUSE#{warehouse_id}"


def pk_drone(drone_id: str) -> str:
    return f"DRONE#{drone_id}"


def pk_inspection(inspection_id: str) -> str:
    return f"INSPECTION#{inspection_id}"


SK_METADATA = "METADATA"


def sk_image(image_id: str) -> str:
    return f"IMAGE#{image_id}"


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------


def put_item(item: Dict[str, Any]) -> None:
    """Write an item to the table.

    Args:
        item: Full DynamoDB item dict (must include PK and SK).
    """
    _table.put_item(Item=item)


def get_item(pk: str, sk: str) -> Optional[Dict[str, Any]]:
    """Fetch a single item by its primary key.

    Args:
        pk: Partition key value.
        sk: Sort key value.

    Returns:
        The item dict, or None if not found.
    """
    response = _table.get_item(Key={"PK": pk, "SK": sk})
    return response.get("Item")


def query_by_pk(pk: str, sk_prefix: Optional[str] = None) -> List[Dict[str, Any]]:
    """Query items sharing the same PK, optionally filtering SK by prefix.

    Args:
        pk: Partition key value.
        sk_prefix: If provided, only items whose SK begins_with this prefix.

    Returns:
        List of matching item dicts.
    """
    key_cond = Key("PK").eq(pk)
    if sk_prefix:
        key_cond = key_cond & Key("SK").begins_with(sk_prefix)

    response = _table.query(KeyConditionExpression=key_cond)
    return response.get("Items", [])


def query_gsi(
    gsi_name: str,
    pk_attr: str,
    pk_value: str,
    sk_attr: Optional[str] = None,
    sk_prefix: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Query a GSI.

    Args:
        gsi_name   : Name of the GSI (e.g. "GSI1" or "GSI2").
        pk_attr    : Name of the GSI partition key attribute (e.g. "GSI1PK").
        pk_value   : Value to match on the GSI partition key.
        sk_attr    : Name of the GSI sort key attribute (optional).
        sk_prefix  : begins_with prefix for the sort key (optional).

    Returns:
        List of matching item dicts.
    """
    key_cond = Key(pk_attr).eq(pk_value)
    if sk_attr and sk_prefix:
        key_cond = key_cond & Key(sk_attr).begins_with(sk_prefix)

    response = _table.query(
        IndexName=gsi_name,
        KeyConditionExpression=key_cond,
    )
    return response.get("Items", [])
