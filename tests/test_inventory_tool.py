import unittest
from inventory_tool import check_warehouse_inventory


class TestInventoryTool(unittest.TestCase):

    def test_available_part(self):
        result = check_warehouse_inventory("Cooling Fan")

        self.assertEqual(result["status"], "available")
        self.assertEqual(result["part_id"], "P101")
        self.assertGreater(result["stock_count"], 0)

    def test_out_of_stock_part(self):
        result = check_warehouse_inventory("Hydraulic Pump")

        self.assertEqual(result["status"], "out_of_stock")
        self.assertEqual(result["stock_count"], 0)

    def test_unknown_part(self):
        result = check_warehouse_inventory("Unknown Spare Part")

        self.assertEqual(result["status"], "part_not_found")

    def test_part_name_with_spaces_and_lowercase(self):
        result = check_warehouse_inventory("  cooling fan  ")

        self.assertEqual(result["status"], "available")
        self.assertEqual(result["part_id"], "P101")


if __name__ == "__main__":
    unittest.main()