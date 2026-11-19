"""End-to-end functional checks against the committed frozen rental snapshot.

Run at repository root:
    PYTHONPATH=src python -m unittest discover -s tests -p 'test_functional.py' -v
No API calls or modifications to frozen files are made.
"""
import json
from pathlib import Path
import unittest

from ucsd_rentals.data import load_snapshot, prepare_data, group_summary

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / 'data' / 'frozen' / 'ucsd_rentals_2026-11-16_102139_PT' / 'rentals.sqlite'
SUMMARY = ROOT / 'results' / 'member_a' / 'summary.json'
PLOTS = ROOT / 'results' / 'member_a'


class FunctionalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = load_snapshot(SNAPSHOT)
        cls.prepared = prepare_data(cls.source)
        cls.summary = json.loads(SUMMARY.read_text(encoding='utf-8'))

    def test_ft01_data_loading_validation(self):
        """FR-01: frozen database loads without losing IDs or missing-area records."""
        self.assertEqual(len(self.source), 2690)
        self.assertEqual(len(self.prepared), len(self.source))
        self.assertTrue(self.source['id'].is_unique)
        self.assertFalse(self.source['id'].isna().any())
        self.assertEqual(self.source['id'].tolist(), self.prepared['id'].tolist())
        self.assertEqual(int(self.prepared['area_missing'].sum()), 85)
        self.assertEqual(int(self.prepared['eligible_for_rent_analysis'].sum()), 2690)
        self.assertEqual(int(self.prepared['eligible_for_area_analysis'].sum()), 2605)

    def test_ft02_analysis_and_visualization(self):
        """FR-03: published rent summaries match computed results and plots exist."""
        eligible = self.prepared.loc[self.prepared['eligible_for_rent_analysis']]
        by_bedrooms = group_summary(eligible, 'bedroom_label')
        self.assertEqual(int(by_bedrooms['n_valid'].sum()), 2690)
        self.assertEqual(int(by_bedrooms['n_records'].sum()), 2690)
        self.assertAlmostEqual(float(eligible['monthly_rent_usd'].median()), 3295.0)
        self.assertAlmostEqual(float(eligible['monthly_rent_usd'].median()),
                               self.summary['monthly_rent_median_usd'])
        self.assertEqual(self.summary['area_analysis_n'], 2605)
        self.assertEqual(self.summary['missing_area_n'], 85)
        for name in ('rent_by_bedrooms.png', 'rent_by_distance.png'):
            path = PLOTS / name
            self.assertTrue(path.is_file(), f'Missing generated plot: {path}')
            self.assertGreater(path.stat().st_size, 0)

    def test_ft03_missing_database_error(self):
        """NFR-03: missing dataset reports failure, without silently returning rows."""
        nonexistent = ROOT / 'data' / 'frozen' / '__missing_database__.sqlite'
        self.assertFalse(nonexistent.exists())
        with self.assertRaises(Exception):
            load_snapshot(nonexistent)


if __name__ == '__main__':
    unittest.main()
