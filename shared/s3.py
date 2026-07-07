"""
shared/s3.py
------------
S3 client and pre-signed URL helpers for the Drone Inspection service.

Design principle:
    Lambdas NEVER handle image bytes.
    They only generate pre-signed PUT URLs so clients upload directly to S3.
"""

import os
from typing import Any, Dict, List

import boto3
from botocore.exceptions import ClientError

# ---------------------------------------------------------------------------
# Client — credentials come from Lambda execution role automatically
# ---------------------------------------------------------------------------

_BUCKET_NAME: str = os.environ["BUCKET_NAME"]
_REGION: str = os.environ.get("AWS_REGION", "ap-south-1")
_URL_EXPIRY: int = int(os.environ.get("PRESIGNED_URL_EXPIRY_SECONDS", "3600"))

_s3_client = boto3.client("s3", region_name=_REGION)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def build_s3_key(inspection_id: str, image_id: str, file_name: str) -> str:
    """Construct a consistent S3 object key.

    Pattern: inspections/<inspection_id>/<image_id>/<file_name>
    Keeps images grouped by inspection for easy listing.
    """
    return f"inspections/{inspection_id}/{image_id}/{file_name}"


def generate_presigned_put_url(
    s3_key: str,
    content_type: str,
    expiry: int = _URL_EXPIRY,
) -> str:
    """Generate a pre-signed PUT URL so the client can upload directly to S3.

    Args:
        s3_key      : Full S3 object key.
        content_type: MIME type the client will use when uploading (e.g. image/jpeg).
        expiry      : URL validity in seconds (default from env, 1 hour).

    Returns:
        Pre-signed URL string.

    Raises:
        ClientError: If boto3 cannot generate the URL.
    """
    url = _s3_client.generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": _BUCKET_NAME,
            "Key": s3_key,
            "ContentType": content_type,
        },
        ExpiresIn=expiry,
    )
    return url


def generate_presigned_get_url(s3_key: str, expiry: int = _URL_EXPIRY) -> str:
    """Generate a pre-signed GET URL so the client can download an image.

    Args:
        s3_key : Full S3 object key.
        expiry : URL validity in seconds.

    Returns:
        Pre-signed URL string.
    """
    url = _s3_client.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": _BUCKET_NAME, "Key": s3_key},
        ExpiresIn=expiry,
    )
    return url


def list_objects_by_prefix(prefix: str) -> List[Dict[str, Any]]:
    """List S3 objects under a given prefix.

    Args:
        prefix: S3 key prefix (e.g. "inspections/<id>/").

    Returns:
        List of S3 object metadata dicts (Key, Size, LastModified).
    """
    response = _s3_client.list_objects_v2(Bucket=_BUCKET_NAME, Prefix=prefix)
    contents = response.get("Contents", [])
    return [
        {
            "s3_key": obj["Key"],
            "size_bytes": obj["Size"],
            "last_modified": obj["LastModified"].isoformat(),
        }
        for obj in contents
    ]
