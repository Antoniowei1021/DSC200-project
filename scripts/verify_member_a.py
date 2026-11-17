"""Check generated Member A outputs against the frozen source, without an API."""

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import statistics

from verify_snapshot import main as verify_snapshot

ROOT = Path(__file__).resolve().parent.parent
FROZEN = ROOT / "data/frozen/ucsd_rentals_2026-11-16_102139_PT"
OUTPUT = ROOT / "results/member_a"
PROCESSED = ROOT / "data/processed/member_a"


def read_only(path):
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)


def main():
    verify_snapshot()
    checks = []

    def check(name, passed, details):
        checks.append({"check": name, "passed": bool(passed), "details": details})
        if not passed:
            raise AssertionError(name)

    with read_only(FROZEN / "rentals.sqlite") as source, read_only(
        PROCESSED / "analysis.sqlite"
    ) as derived:
        columns = [row[1] for row in source.execute("PRAGMA table_info(listings)")]
        selected = ", ".join('"' + column + '"' for column in columns)
        original = source.execute(
            f"SELECT {selected} FROM listings ORDER BY id"
        ).fetchall()
        preserved = derived.execute(
            f"SELECT {selected} FROM analysis_listings ORDER BY id"
        ).fetchall()
        check("original_columns_and_rows_preserved", original == preserved,
              {"rows": len(original), "source_columns": len(columns)})

        counts = derived.execute(
            "SELECT COUNT(*), COUNT(DISTINCT id), "
            "SUM(eligible_for_rent_analysis), SUM(eligible_for_area_analysis) "
            "FROM analysis_listings"
        ).fetchone()
        check("expected_analysis_denominators", counts == (2690, 2690, 2690, 2605),
              {"actual": counts, "expected": [2690, 2690, 2690, 2605]})
        missing = derived.execute(
            "SELECT COUNT(*), SUM(eligible_for_rent_analysis), "
            "SUM(rent_per_sqft_usd IS NULL) FROM analysis_listings "
            "WHERE squareFootage IS NULL"
        ).fetchone()
        check("missing_area_keeps_monthly_rent", missing == (85, 85, 85),
              {"missing_area_rows": missing[0], "retained_for_rent": missing[1],
               "missing_unit_price": missing[2]})

        prices = [row[0] for row in source.execute("SELECT price FROM listings")]
        summary = json.loads((OUTPUT / "summary.json").read_text())
        check("overall_median_independently_recomputed",
              statistics.median(prices) == summary["monthly_rent_median_usd"],
              {"stdlib_median": statistics.median(prices)})
        bedrooms = json.loads((OUTPUT / "rent_by_bedrooms.json").read_text())
        for row in bedrooms:
            values = [r[0] for r in source.execute(
                "SELECT price FROM listings WHERE bedrooms = ?", (row["bedroom_count"],)
            )]
            check(f"bedroom_{row['bedroom_count']}_median_and_count",
                  row["n_valid"] == len(values)
                  and row["median"] == statistics.median(values),
                  {"n": len(values), "median": statistics.median(values)})

        distance_error = derived.execute(
            "SELECT MAX(ABS(distance_miles - distanceToCampusMiles)) "
            "FROM analysis_listings"
        ).fetchone()[0]
        check("distance_matches_frozen_reference", distance_error < 1e-9,
              {"max_absolute_difference_miles": distance_error})
        raw_json = json.loads((PROCESSED / "analysis_listings.json").read_text())
        ids = [row[0] for row in original]
        check("json_ids_and_nulls_match_database",
              [row["id"] for row in raw_json] == ids
              and sum(row["rent_per_sqft_usd"] is None for row in raw_json) == 85,
              {"json_rows": len(raw_json)})

        flags = derived.execute(
            "SELECT SUM(room_wording_review), SUM(area_extreme_review), "
            "SUM(long_market_review) FROM analysis_listings"
        ).fetchone()
        check("review_counts_match_independent_audit", flags == (2, 12, 346),
              {"actual": flags, "expected": [2, 12, 346]})

    for filename in ["rent_by_bedrooms.png", "rent_by_bedrooms.pdf",
                     "rent_by_distance.png", "rent_by_distance.pdf"]:
        check(f"artifact_{filename}", (OUTPUT / filename).stat().st_size > 1000,
              {"bytes": (OUTPUT / filename).stat().st_size})

    evidence = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "kind": "integration and data audit; not additional rubric unit cases",
        "all_passed": all(row["passed"] for row in checks),
        "checks": checks,
    }
    (OUTPUT / "integration_checks.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(f"PASS: {len(checks)} integration/data checks; frozen baseline unchanged.")


if __name__ == "__main__":
    main()
