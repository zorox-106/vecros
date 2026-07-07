"""
tests/test_create_inspection.py
---------------------------------
Unit tests for the Create Inspection Lambda handler.
Uses unittest.mock to patch DynamoDB — no real AWS calls.
"""

import json
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Ensure shared/ and lambdas/ are importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Patch env vars before importing the handler
os.environ.setdefault("TABLE_NAME", "DroneInspectionTable-test")
os.environ.setdefault("BUCKET_NAME", "vecros-test-bucket")


class TestCreateInspection(unittest.TestCase):

    def _make_event(self, body: dict) -> dict:
        return {"body": json.dumps(body), "pathParameters": None}

    @patch("shared.db._table")
    def test_creates_inspection_successfully(self, mock_table):
        """Should return 201 with the new inspection object."""
        mock_table.put_item = MagicMock(return_value={})

        from lambdas.create_inspection.handler import lambda_handler

        event = self._make_event(
            {"warehouse_id": "wh-001", "drone_id": "drone-001", "notes": "Test run"}
        )
        result = lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 201)
        body = json.loads(result["body"])
        self.assertEqual(body["warehouse_id"], "wh-001")
        self.assertEqual(body["drone_id"], "drone-001")
        self.assertIn("inspection_id", body)
        self.assertIn("created_at", body)
        mock_table.put_item.assert_called_once()

    @patch("shared.db._table")
    def test_missing_warehouse_id_returns_400(self, mock_table):
        """Should return 400 when warehouse_id is absent."""
        from lambdas.create_inspection.handler import lambda_handler

        event = self._make_event({"drone_id": "drone-001"})
        result = lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 400)
        body = json.loads(result["body"])
        self.assertIn("warehouse_id", body["details"])
        mock_table.put_item.assert_not_called()

    @patch("shared.db._table")
    def test_missing_drone_id_returns_400(self, mock_table):
        """Should return 400 when drone_id is absent."""
        from lambdas.create_inspection.handler import lambda_handler

        event = self._make_event({"warehouse_id": "wh-001"})
        result = lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 400)

    @patch("shared.db._table")
    def test_invalid_json_body_returns_400(self, mock_table):
        """Should return 400 for malformed JSON."""
        from lambdas.create_inspection.handler import lambda_handler

        event = {"body": "not-valid-json", "pathParameters": None}
        result = lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 400)

    @patch("shared.db._table")
    def test_dynamodb_error_returns_500(self, mock_table):
        """Should return 500 when DynamoDB raises an exception."""
        mock_table.put_item = MagicMock(side_effect=Exception("DynamoDB unavailable"))

        from lambdas.create_inspection.handler import lambda_handler

        event = self._make_event({"warehouse_id": "wh-001", "drone_id": "drone-001"})
        result = lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 500)


if __name__ == "__main__":
    unittest.main()
