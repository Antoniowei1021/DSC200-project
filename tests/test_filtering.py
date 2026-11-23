"""Member B: FR-02 filtering tests with synthetic data (offline).

Run from repository root:
    PYTHONPATH=src python -m unittest tests.test_filtering -v
"""

from pathlib import Path
import math
import sqlite3
import subprocess
import sys
import tempfile
import unittest

import pandas as pd

from ucsd_rentals.filtering import filter_listings

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/filter_listings.py"


class FilteringTests(unittest.TestCase):
    def setUp(self):
        self.listings = pd.DataFrame({
            "id": ["A", "B", "C", "D", "E", "F", "G"],
            "formattedAddress": ["test"] * 7,
            "monthly_rent_usd": [2200, 2500, 3000, 2700, 2300, 2300, math.nan],
            "bedroom_count": [0, 2, 2, 1, 2, 2, 2],
            "distance_miles": [1.0, 5.0, 8.0, 10.0, 4.0, 10.1, 3.0],
            "area_sqft": [400, 900, 1000, math.nan, 800, 700, 900],
            "eligible_for_rent_analysis": [1, 1, 1, 1, 0, 1, 1],
        })

    def test_no_filters_returns_all_eligible_within_ten_miles(self):
        result = filter_listings(self.listings)
        self.assertEqual(result["id"].tolist(), ["A", "B", "C", "D"])
        self.assertEqual(len(result.columns), len(self.listings.columns))

    def test_all_filters_are_and_combined_and_inclusive(self):
        result = filter_listings(
            self.listings, max_monthly_rent=2500, bedrooms=2, max_distance_miles=5
        )
        self.assertEqual(result["id"].tolist(), ["B"])
        self.assertEqual(float(result.iloc[0]["monthly_rent_usd"]), 2500)
        self.assertEqual(float(result.iloc[0]["distance_miles"]), 5)

    def test_studio_and_unset_distance(self):
        self.assertEqual(
            filter_listings(self.listings, bedrooms=0)["id"].tolist(), ["A"]
        )
        self.assertEqual(
            filter_listings(self.listings, bedrooms=1)["id"].tolist(), ["D"]
        )
        # A larger radius does not expand the 10-mile frozen dataset.
        self.assertEqual(
            filter_listings(self.listings, max_distance_miles=20)["id"].tolist(),
            ["A", "B", "C", "D"],
        )

    def test_missing_area_remains_eligible_for_rent_filter(self):
        result = filter_listings(self.listings, bedrooms=1)
        self.assertEqual(result["id"].tolist(), ["D"])
        self.assertTrue(pd.isna(result.iloc[0]["area_sqft"]))

    def test_no_matches_returns_empty_frame_with_columns(self):
        result = filter_listings(self.listings, max_monthly_rent=100)
        self.assertTrue(result.empty)
        self.assertEqual(result.columns.tolist(), self.listings.columns.tolist())

    def test_invalid_filter_parameters_raise_clear_errors(self):
        invalid = (
            {"max_monthly_rent": -1},
            {"max_monthly_rent": "2500"},
            {"max_monthly_rent": math.nan},
            {"max_monthly_rent": math.inf},
            {"max_monthly_rent": True},
            {"bedrooms": -2},
            {"bedrooms": 1.5},
            {"bedrooms": "2"},
            {"bedrooms": False},
            {"max_distance_miles": -1},
            {"max_distance_miles": "5"},
            {"max_distance_miles": math.inf},
        )
        for condition in invalid:
            with self.subTest(condition=condition):
                with self.assertRaisesRegex(ValueError, "must be"):
                    filter_listings(self.listings, **condition)

    def test_missing_columns_and_duplicate_ids_raise_errors(self):
        with self.assertRaisesRegex(ValueError, "Missing required analysis columns"):
            filter_listings(self.listings.drop(columns=["distance_miles"]))
        with self.assertRaisesRegex(ValueError, "Listing IDs"):
            changed = self.listings.copy()
            changed.loc[1, "id"] = "A"
            filter_listings(changed)

    def test_input_is_not_mutated_and_output_is_independent(self):
        before = self.listings.copy(deep=True)
        result = filter_listings(self.listings, max_monthly_rent=2500)
        result.loc[:, "monthly_rent_usd"] = 99
        pd.testing.assert_frame_equal(self.listings, before)

    def test_cli_reads_sqlite_and_exports_csv(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            database = folder / "analysis.sqlite"
            output = folder / "matches.csv"
            with sqlite3.connect(database) as connection:
                self.listings.to_sql("analysis_listings", connection, index=False)
            completed = subprocess.run(
                [sys.executable, str(SCRIPT), "--database", str(database),
                 "--max-rent", "2500", "--bedrooms", "2",
                 "--max-distance", "5", "--output", str(output)],
                cwd=ROOT, capture_output=True, text=True, check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("Matching listings: 1 / 7", completed.stdout)
            exported = pd.read_csv(output)
            self.assertEqual(exported["id"].tolist(), ["B"])
            self.assertEqual(float(exported.iloc[0]["monthly_rent_usd"]), 2500)

    def test_cli_no_matches_and_missing_db(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            database = folder / "analysis.sqlite"
            output = folder / "matches.csv"
            with sqlite3.connect(database) as connection:
                self.listings.to_sql("analysis_listings", connection, index=False)
            empty = subprocess.run(
                [sys.executable, str(SCRIPT), "--database", str(database),
                 "--max-rent", "100", "--output", str(output)],
                cwd=ROOT, capture_output=True, text=True, check=False,
            )
            self.assertEqual(empty.returncode, 0, empty.stderr)
            self.assertIn("Matching listings: 0", empty.stdout)
            self.assertTrue(pd.read_csv(output).empty)
            missing = subprocess.run(
                [sys.executable, str(SCRIPT), "--database", str(folder / "missing.sqlite")],
                cwd=ROOT, capture_output=True, text=True, check=False,
            )
            self.assertNotEqual(missing.returncode, 0)
            self.assertIn("Run 'python scripts/run_member_a.py' first", missing.stderr)


if __name__ == "__main__":
    unittest.main()
