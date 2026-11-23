# Member B — Rental Listing Filtering MVP (FR-02)

This is a **small add-on** to the existing `Antoniowei1021/DSC200-project` repository.
It uses Member A's preprocessed SQLite data and does not require a new RentCast API request.

## File locations in the existing repository

Copy these files to the **same relative paths** in the repository:

- `src/ucsd_rentals/filtering.py` — pure filtering function, returns a DataFrame.
- `scripts/filter_listings.py` — command-line driver that reads derived SQLite read-only and exports a CSV.
- `tests/test_filtering.py` — 10 synthetic unit/CLI tests.
- `docs/member_b_filtering_mvp.md` — this documentation.

Existing `src/ucsd_rentals/data.py` and all frozen data remain untouched.

## Setup and usage

From the **repository root**:

```bash
python -m pip install -r requirements-analysis.txt
python scripts/run_member_a.py
PYTHONPATH=src python -m unittest tests.test_filtering -v
python scripts/filter_listings.py --max-rent 2500 --bedrooms 2 --max-distance 5
```

On Windows PowerShell, set `$env:PYTHONPATH="src"` before running the tests.

Default output: `results/member_b/filtered_listings.csv`.
Use `--output path/to/file.csv` to choose a different destination.

For **all eligible listings within 10 miles, regardless of bedroom count**, run:

```bash
python scripts/filter_listings.py
```

You may omit any combination of `--max-rent`, `--bedrooms`, and `--max-distance`.
For studios use `--bedrooms 0`. All specified conditions are combined with AND.

The Python API is:

```python
from ucsd_rentals.filtering import filter_listings

matches = filter_listings(
    prepared_dataframe,
    max_monthly_rent=2500,  # optional inclusive upper bound
    bedrooms=2,             # optional exact count
    max_distance_miles=5,   # optional inclusive straight-line radius
)
```

## FR-02 acceptance criteria

| Criterion | MVP behavior / evidence |
| --- | --- |
| Optional parameters | All three parameters default to `None`; with none, all eligible records within 10 miles are returned. |
| AND semantics | Every specified constraint must be satisfied. |
| Rent boundary | `monthly_rent_usd <= max_monthly_rent` (inclusive). |
| Bedrooms | Exact numeric match; `0` means a studio. |
| Distance | `distance_miles <= max_distance_miles` (inclusive). The dataset itself never extends beyond 10 miles. |
| Invalid inputs | `ValueError` with a clear parameter name for negative, nonfinite, string, boolean or non-integer counts. |
| No matches | Return an empty DataFrame; CLI exports a header-only CSV. |
| Data integrity | Preserve listing IDs, original columns and relative row order; no changes to frozen SQLite data. |
| Missing area | Listing stays in results if it qualifies for monthly-rent analysis, even if `area_sqft` is missing. |

The MVP uses `eligible_for_rent_analysis` from Member A's preparation and checks
finite positive rent plus the 10-mile geographic restriction. It deliberately
does not apply `eligible_for_area_analysis`: a listing with missing area can still
be matched by budget, bedroom count, and distance.

### Practical limits

- The stored listings represent advertised rentals from the **Nov 16, 2026 frozen snapshot**, not verified currently available properties.
- This is a CLI / reusable-function MVP, **not a graphical map UI**. The optional distance criterion uses straight-line miles, not travel time.
- Filter output includes comparison columns but does not compute rent per person or predict future prices.
- A radius larger than 10 miles is accepted, but cannot return rentals outside the existing dataset. If no radius is supplied, the full eligible 10-mile snapshot is used.
- No external APIs, live listings, or automatic data collection are used.

## Tests and team handoff

`tests/test_filtering.py` uses small synthetic fixtures and a temporary SQLite file.
It covers inclusive bounds, multiple filters, studios, missing floor area, invalid
values, input immutability, empty results, read-only data access and CSV export.
Run it separately from existing `tests/test_member_a.py` and `tests/test_functional.py`.

The current `functional_test_cases.md` describes FT-02 as **price analysis**, while
`docs/member_B_requirements.md` suggests FT-02 for **filtering**. Before final M2
submission, Member C should reconcile test identifiers and map the executed tests
to the final requirements. Do not claim a live-data functional filtering test was
executed solely based on the synthetic tests in this package.

Add an AI-assistance disclosure covering this module and tests according to the
course policy. The required personal reflection must be written by the students.
