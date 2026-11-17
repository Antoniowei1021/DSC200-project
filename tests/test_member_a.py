"""Three Member A unit test cases for the M2 submission.

Run from the repository root with:
    PYTHONPATH=src python3 -m unittest tests.test_member_a -v

The examples are hand-calculated fixtures, independent of the frozen dataset.
"""
import math
import unittest

import pandas as pd

from ucsd_rentals.data import group_summary, unit_rent


class MemberAUnitTests(unittest.TestCase):
    def test_ut_a1_unit_rent_valid_area(self):
        """UT-A1: $3,000 / 1,000 sqft gives $3.00 per sqft per month."""
        result = unit_rent(3000, 1000)
        self.assertAlmostEqual(result, 3.0, places=10)

    def test_ut_a2_unit_rent_missing_or_invalid_area(self):
        """UT-A2: unusable area gives None, without a division error."""
        for area in (None, 0, -100, math.nan, math.inf, -math.inf):
            with self.subTest(area=area):
                self.assertIsNone(unit_rent(3000, area))

    def test_ut_a3_grouped_medians_ignore_missing_values(self):
        """UT-A3: grouped medians and valid/missing counts match known values."""
        fixture = pd.DataFrame({
            "bedroom_group": ["Studio", "1 bedroom", "Studio", "1 bedroom",
                              "Studio", "1 bedroom", "1 bedroom"],
            "monthly_rent_usd": [1000, 1800, 3000, 2200, None, 8000, None],
        })

        summary = group_summary(fixture, "bedroom_group").set_index("bedroom_group")

        self.assertEqual(set(summary.index), {"Studio", "1 bedroom"})
        studio = summary.loc["Studio"]
        # Two valid values: the median is their midpoint, not the lower value.
        self.assertEqual(studio["n_records"], 3)
        self.assertEqual(studio["n_valid"], 2)
        self.assertEqual(studio["n_missing"], 1)
        self.assertAlmostEqual(studio["median"], 2000.0)
        one_bedroom = summary.loc["1 bedroom"]
        # Three valid values: missing rent is not included as zero.
        self.assertEqual(one_bedroom["n_records"], 4)
        self.assertEqual(one_bedroom["n_valid"], 3)
        self.assertEqual(one_bedroom["n_missing"], 1)
        self.assertAlmostEqual(one_bedroom["median"], 2200.0)


if __name__ == "__main__":
    unittest.main()
