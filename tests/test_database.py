import unittest
import tempfile

from pathlib import Path
from unittest.mock import patch

import database


class TestComplaintDatabase(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_db_path = (
            Path(self.temp_dir.name) / "test.db"
        )

        self.db_patcher = patch(
            "database.DB_PATH",
            self.test_db_path
        )
        self.db_patcher.start()

        database.init_db()

    def tearDown(self):
        self.db_patcher.stop()
        self.temp_dir.cleanup()

    def test_save_and_retrieve_complaint(self):
        record_id = database.save_complaint(
            complaint="Machine is overheating",
            diagnosis="Cooling fan may have failed",
            inventory="12 units available",
            recommended_part="Cooling Fan",
            availability="Available",
            part_id="P101",
            stock_quantity="12",
            warehouse_location="Aisle A3",
        )

        self.assertIsNotNone(record_id)

        records = database.get_recent_complaints()

        self.assertEqual(len(records), 1)
        self.assertEqual(
            records[0]["complaint"],
            "Machine is overheating"
        )
        self.assertEqual(
            records[0]["part_id"],
            "P101"
        )
        self.assertEqual(
            records[0]["stock_quantity"],
            "12"
        )

    def test_empty_database(self):
        records = database.get_recent_complaints()
        self.assertEqual(records, [])


    def _save_sample_complaint(self, complaint):
        return database.save_complaint(
        complaint=complaint,
        diagnosis=f"Diagnosis for {complaint}",
        inventory="Inventory verified",
        recommended_part="Cooling Fan",
        availability="Available",
        part_id="P101",
        stock_quantity="12",
        warehouse_location="Aisle A3",
    )


    def test_recent_complaints_order_and_limit(self):
        self._save_sample_complaint("First complaint")
        self._save_sample_complaint("Second complaint")
        self._save_sample_complaint("Third complaint")

        records = database.get_recent_complaints(limit=2)

        self.assertEqual(len(records), 2)
        self.assertEqual(
            records[0]["complaint"],
            "Third complaint",
        )
        self.assertEqual(
            records[1]["complaint"],
            "Second complaint",
        )


if __name__ == "__main__":
    unittest.main()