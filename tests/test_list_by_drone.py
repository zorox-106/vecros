"""
tests/test_list_by_drone.py
-----------------------------
Unit tests for List Inspections by Drone Lambda.
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
        "PK": "INSPECTION#xyz",
        "SK": "METADATA",
        "inspection_id": "xyz",
        "warehouse_id": "wh-002",
        "drone_id": "drone-007",
        "notes": "Sector B sweep",
        "status": "CREATED",
        "created_at": "2026-07-07T09:00:00+00:00",
    }
]


class TestListByDrone(unittest.TestCase):

    def _make_event(self, drone_id: str) -> dict:
        return {
            "pathParameters": {"drone_id": drone_id},
            "body": None,
        }

    @patch("shared.db._table")
    def test_returns_inspections_for_drone(self, mock_table):
        """Should return inspections performed by the drone."""
        mock_table.query = MagicMock(return_value={"Items": SAMPLE_ITEMS})

        from lambdas.list_by_drone.handler import lambda_handler

        result = lambda_handler(self._make_event("drone-007"), None)

        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertEqual(body["drone_id"], "drone-007")
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["inspections"][0]["inspection_id"], "xyz")

    @patch("shared.db._table")
    def test_returns_empty_when_no_inspections(self, mock_table):
        """Should return empty list when drone has no inspections."""
        mock_table.query = MagicMock(return_value={"Items": []})

        from lambdas.list_by_drone.handler import lambda_handler

        result = lambda_handler(self._make_event("drone-999"), None)

        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertEqual(body["count"], 0)

    def test_missing_drone_id_returns_400(self):
        """Should return 400 when drone_id path param is missing."""
        from lambdas.list_by_drone.handler import lambda_handler

        event = {"pathParameters": {}, "body": None}
        result = lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 400)

    @patch("shared.db._table")
    def test_dynamodb_error_returns_500(self, mock_table):
        """Should return 500 on DynamoDB failure."""
        mock_table.query = MagicMock(side_effect=Exception("Throttled"))

        from lambdas.list_by_drone.handler import lambda_handler

        result = lambda_handler(self._make_event("drone-007"), None)

        self.assertEqual(result["statusCode"], 500)


if __name__ == "__main__":
    unittest.main()
