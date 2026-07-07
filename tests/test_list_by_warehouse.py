"""
tests/test_list_by_warehouse.py
---------------------------------
Unit tests for List Inspections by Warehouse Lambda.
"""

import json
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("TABLE_NAME", "DroneInspectionTable-test")
os.environ.setdefault("BUCKET_NAME", "vecros-test-bucket")

SAMPLE_ITEMS = [
    {
        "PK": "INSPECTION#abc",
        "SK": "METADATA",
        "inspection_id": "abc",
        "warehouse_id": "wh-001",
        "drone_id": "drone-001",
        "notes": "Row A check",
        "status": "CREATED",
        "created_at": "2026-07-07T08:00:00+00:00",
    }
]


class TestListByWarehouse(unittest.TestCase):

    def _make_event(self, warehouse_id: str) -> dict:
        return {
            "pathParameters": {"warehouse_id": warehouse_id},
            "body": None,
        }

    @patch("shared.db._table")
    def test_returns_inspections_for_warehouse(self, mock_table):
        """Should return a list of inspections for the given warehouse."""
        mock_table.query = MagicMock(return_value={"Items": SAMPLE_ITEMS})

        from lambdas.list_by_warehouse.handler import lambda_handler

        result = lambda_handler(self._make_event("wh-001"), None)

        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertEqual(body["warehouse_id"], "wh-001")
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["inspections"][0]["inspection_id"], "abc")

    @patch("shared.db._table")
    def test_returns_empty_list_when_no_inspections(self, mock_table):
        """Should return empty list when warehouse has no inspections."""
        mock_table.query = MagicMock(return_value={"Items": []})

        from lambdas.list_by_warehouse.handler import lambda_handler

        result = lambda_handler(self._make_event("wh-999"), None)

        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertEqual(body["count"], 0)
        self.assertEqual(body["inspections"], [])

    def test_missing_warehouse_id_returns_400(self):
        """Should return 400 when warehouse_id path param is absent."""
        from lambdas.list_by_warehouse.handler import lambda_handler

        event = {"pathParameters": {}, "body": None}
        result = lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 400)

    @patch("shared.db._table")
    def test_dynamodb_error_returns_500(self, mock_table):
        """Should return 500 when DynamoDB raises."""
        mock_table.query = MagicMock(side_effect=Exception("Connection timeout"))

        from lambdas.list_by_warehouse.handler import lambda_handler

        result = lambda_handler(self._make_event("wh-001"), None)

        self.assertEqual(result["statusCode"], 500)


if __name__ == "__main__":
    unittest.main()
