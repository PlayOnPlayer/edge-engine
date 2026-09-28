import unittest

from edge_engine.fees import maker_rebate, taker_fee


class FeeTests(unittest.TestCase):
    def test_current_us_midpoint_schedule(self):
        self.assertEqual(taker_fee(0.50, 100), 1.74)
        self.assertEqual(maker_rebate(0.50, 100), 0.31)

    def test_banker_rounding_near_extreme(self):
        self.assertEqual(taker_fee(0.01, 100), 0.07)


if __name__ == "__main__":
    unittest.main()

