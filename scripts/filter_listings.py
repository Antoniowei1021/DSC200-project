"""Run FR-02 rental-listing filtering on Member A's derived SQLite data.

From the repository root:
    python scripts/run_member_a.py
    python scripts/filter_listings.py --max-rent 2500 --bedrooms 2 --max-distance 5
"""

import argparse
from pathlib import Path
import sqlite3
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ucsd_rentals.filtering import filter_listings

DEFAULT_DATABASE = ROOT / "data/processed/member_a/analysis.sqlite"
DEFAULT_OUTPUT = ROOT / "results/member_b/filtered_listings.csv"
FROZEN_DIRECTORY = ROOT / "data/frozen"
EXPORT_COLUMNS = [
    "id",
    "formattedAddress",
    "monthly_rent_usd",
    "bedroom_count",
    "bathroom_count",
    "area_sqft",
    "distance_miles",
    "rent_per_sqft_usd",
    "propertyType",
    "zipCode",
]


def load_analysis_listings(path):
    """Load Member A's analysis data without allowing SQLite writes."""
    path = Path(path).resolve()
    if not path.is_file():
        raise FileNotFoundError(
            f"Processed database not found: {path}. "
            "Run 'python scripts/run_member_a.py' first."
        )
    try:
        with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
            return pd.read_sql_query("SELECT * FROM analysis_listings ORDER BY id", db)
    except (sqlite3.Error, pd.errors.DatabaseError) as error:
        raise RuntimeError(f"Cannot read analysis_listings from {path}: {error}") from error


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE,
                        help="Member A processed SQLite database (read-only)")
    parser.add_argument("--max-rent", type=float, default=None,
                        help="Maximum advertised monthly rent in USD (inclusive)")
    parser.add_argument("--bedrooms", type=int, default=None,
                        help="Exact bedroom count (0 = studio)")
    parser.add_argument("--max-distance", type=float, default=None,
                        help="Maximum straight-line distance from UCSD in miles")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="Output CSV; can contain only a header if no matches")
    args = parser.parse_args(argv)

    output = args.output.resolve()
    frozen = FROZEN_DIRECTORY.resolve()
    if output == frozen or frozen in output.parents:
        parser.error("Output must not be written inside data/frozen")

    try:
        listings = load_analysis_listings(args.database)
        matches = filter_listings(
            listings,
            max_monthly_rent=args.max_rent,
            bedrooms=args.bedrooms,
            max_distance_miles=args.max_distance,
        )
        available = [c for c in EXPORT_COLUMNS if c in matches.columns]
        output.parent.mkdir(parents=True, exist_ok=True)
        matches.loc[:, available].to_csv(output, index=False)
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        parser.error(str(error))

    print(f"Matching listings: {len(matches)} / {len(listings)} records")
    print(f"Saved: {output}")
    if matches.empty:
        print("No listings matched; exported a header-only CSV.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
