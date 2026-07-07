"""
tests/test_presigned_url.py
-----------------------------
Unit tests for Generate Pre-signed URL Lambda.
"""

import json
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("TABLE_NAME", "DroneInspectionTable-test")
os.environ.setdefault("BUCKET_NAME", "vecros-test-bucket")
os.environ.setdefault("PRESIGNED_URL_EXPIRY_SECONDS", "3600")

EXISTING_INSPECTION = {
    "PK": "INSPECTION#insp-001",
    "SK": "METADATA",
    "inspection_id": "insp-001",
    "warehouse_id": "wh-001",
    "drone_id": "drone-001",
    "status": "CREATED",
    "created_at": "2026-07-07T08:00:00+00:00",
}

FAKE_PRESIGNED_URL = "https://s3.amazonaws.com/vecros-test-bucket/inspections/insp-001/img-abc/shelf.jpg?X-Amz-Signature=fake"


class TestGeneratePresignedUrl(unittest.TestCase):

    def _make_event(self, inspection_id: str, body: dict) -> dict:
        return {
            "pathParameters": {"inspection_id": inspection_id},
            "body": json.dumps(body),
        }

    @patch("shared.s3._s3_client")
    @patch("shared.db._table")
    def test_generates_url_successfully(self, mock_table, mock_s3):
        """Should return 200 with a pre-signed URL when inspection exists."""
        # DynamoDB returns the existing inspection on get_item
        mock_table.get_item = MagicMock(return_value={"Item": EXISTING_INSPECTION})
        mock_table.put_item = MagicMock(return_value={})
        # S3 client returns a fake pre-signed URL
        mock_s3.generate_presigned_url = MagicMock(return_value=FAKE_PRESIGNED_URL)

        from lambdas.generate_presigned_url.handler import lambda_handler

        event = self._make_event(
            "insp-001", {"file_name": "shelf.jpg", "content_type": "image/jpeg"}
        )
        result = lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertEqual(body["upload_url"], FAKE_PRESIGNED_URL)
        self.assertIn("image_id", body)
        self.assertIn("s3_key", body)
        self.assertEqual(body["expires_in"], 3600)

    @patch("shared.db._table")
    def test_returns_404_when_inspection_not_found(self, mock_table):
        """Should return 404 when inspection does not exist."""
        mock_table.get_item = MagicMock(return_value={})  # Item key absent = not found

        from lambdas.generate_presigned_url.handler import lambda_handler

        event = self._make_event(
            "nonexistent", {"file_name": "img.jpg", "content_type": "image/jpeg"}
        )
        result = lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 404)

    @patch("shared.db._table")
    def test_missing_file_name_returns_400(self, mock_table):
        """Should return 400 when file_name is not provided."""
        mock_table.get_item = MagicMock(return_value={"Item": EXISTING_INSPECTION})

        from lambdas.generate_presigned_url.handler import lambda_handler

        event = self._make_event("insp-001", {"content_type": "image/jpeg"})
        result = lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 400)

    def test_missing_inspection_id_returns_400(self):
        """Should return 400 when inspection_id path param is absent."""
        from lambdas.generate_presigned_url.handler import lambda_handler

        event = {
            "pathParameters": {},
            "body": json.dumps({"file_name": "img.jpg", "content_type": "image/jpeg"}),
        }
        result = lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 400)


if __name__ == "__main__":
    unittest.main()
