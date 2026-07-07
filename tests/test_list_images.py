"""
tests/test_list_images.py
---------------------------
Unit tests for List Images Lambda.
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
}

SAMPLE_IMAGE_ITEMS = [
    {
        "PK": "INSPECTION#insp-001",
        "SK": "IMAGE#img-001",
        "entity_type": "IMAGE",
        "image_id": "img-001",
        "inspection_id": "insp-001",
        "file_name": "shelf_row_1.jpg",
        "content_type": "image/jpeg",
        "s3_key": "inspections/insp-001/img-001/shelf_row_1.jpg",
        "created_at": "2026-07-07T09:30:00+00:00",
    }
]

FAKE_VIEW_URL = "https://s3.amazonaws.com/vecros-test-bucket/inspections/insp-001/img-001/shelf_row_1.jpg?X-Amz-Signature=fake"


class TestListImages(unittest.TestCase):

    def _make_event(self, inspection_id: str) -> dict:
        return {
            "pathParameters": {"inspection_id": inspection_id},
            "body": None,
        }

    @patch("shared.s3._s3_client")
    @patch("shared.db._table")
    def test_returns_images_with_view_urls(self, mock_table, mock_s3):
        """Should return images enriched with pre-signed GET URLs."""
        mock_table.get_item = MagicMock(return_value={"Item": EXISTING_INSPECTION})
        mock_table.query = MagicMock(return_value={"Items": SAMPLE_IMAGE_ITEMS})
        mock_s3.generate_presigned_url = MagicMock(return_value=FAKE_VIEW_URL)

        from lambdas.list_images.handler import lambda_handler

        result = lambda_handler(self._make_event("insp-001"), None)

        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertEqual(body["inspection_id"], "insp-001")
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["images"][0]["image_id"], "img-001")
        self.assertEqual(body["images"][0]["view_url"], FAKE_VIEW_URL)

    @patch("shared.db._table")
    def test_returns_404_when_inspection_not_found(self, mock_table):
        """Should return 404 when inspection does not exist."""
        mock_table.get_item = MagicMock(return_value={})

        from lambdas.list_images.handler import lambda_handler

        result = lambda_handler(self._make_event("nonexistent"), None)

        self.assertEqual(result["statusCode"], 404)

    @patch("shared.s3._s3_client")
    @patch("shared.db._table")
    def test_returns_empty_list_when_no_images(self, mock_table, mock_s3):
        """Should return empty images list when none exist for the inspection."""
        mock_table.get_item = MagicMock(return_value={"Item": EXISTING_INSPECTION})
        mock_table.query = MagicMock(return_value={"Items": []})

        from lambdas.list_images.handler import lambda_handler

        result = lambda_handler(self._make_event("insp-001"), None)

        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertEqual(body["count"], 0)

    def test_missing_inspection_id_returns_400(self):
        """Should return 400 when inspection_id is absent."""
        from lambdas.list_images.handler import lambda_handler

        event = {"pathParameters": {}, "body": None}
        result = lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 400)


if __name__ == "__main__":
    unittest.main()
