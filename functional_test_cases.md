# Functional Test Cases — DSC 200 San Diego Rental Analysis

**Source:** Frozen RentCast snapshot `ucsd_rentals_2026-11-16_102139_PT` and the requirements in `docs/member_B_requirements.md`. These are **functional/integration-level** checks of real stored data and project outputs, not synthetic unit tests. No live API requests are needed.

**How to run:** From the repository root, install the dependencies in `requirements-analysis.txt` and run:

```bash
PYTHONPATH=src python -m unittest discover -s tests -p 'test_functional.py' -v
```

On Windows PowerShell, run `$env:PYTHONPATH="src"` first, then `python -m unittest discover -s tests -p "test_functional.py" -v`.

## FT-01 — Load and validate frozen rental data (FR-01)

- **Preconditions:** Frozen `rentals.sqlite` is present; required Python dependencies are installed.
- **Input:** The committed 2026-11-16 frozen SQLite snapshot.
- **Steps:** (1) Load the snapshot using `load_snapshot`; (2) run `prepare_data`; (3) compare original and prepared IDs and row counts; (4) inspect missing-area and eligibility flags.
- **Expected result:** 2,690 rows are loaded and retained; listing IDs are unique, non-null and in the same order; 85 records have missing area; 2,690 records remain eligible for monthly-rent analysis and 2,605 for rent-per-area analysis. No records are silently dropped.
- **Postconditions:** Source data remain unchanged; prepared data exist only in memory.
- **Status:** Executable in `test_ft01_data_loading_validation`.

## FT-02 — Rental price analysis and visualization (FR-03)

- **Preconditions:** The frozen snapshot and existing analysis output files under `results/member_a/` are present.
- **Inputs:** All eligible listings from the frozen snapshot and `results/member_a/summary.json`.
- **Steps:** (1) Load and prepare records; (2) group eligible records by bedroom label and compute rent statistics; (3) compare overall median with the saved summary; (4) verify expected valid/excluded area counts; (5) check that bedroom and distance plot PNG files exist and are nonempty.
- **Expected result:** Bedroom groups cover all 2,690 eligible monthly-rent records; overall median monthly rent is $3,295; 2,605 listings are eligible for rent-per-square-foot analysis, with 85 excluded due to missing area; `rent_by_bedrooms.png` and `rent_by_distance.png` exist and are nonempty.
- **Postconditions:** Existing analysis outputs remain available; no frozen data are modified.
- **Status:** Executable in `test_ft02_analysis_and_visualization`. **Limitation:** File existence is checked, but visual clarity, labels and sample sizes still require human inspection of the plots.

## FT-03 — Missing data source is reported (NFR-03)

- **Preconditions:** The application is installed; the deliberately nonexistent test database path is absent.
- **Input:** `data/frozen/__missing_database__.sqlite` (nonexistent path).
- **Steps:** Call `load_snapshot` with the missing path.
- **Expected result:** The operation raises an exception rather than silently returning an empty or fabricated dataset.
- **Postconditions:** No new frozen database is created.
- **Status:** Executable in `test_ft03_missing_database_error`. **Limitation:** This verifies failure signaling, not the exact wording of the error message.

## Test status and scope

This suite contains three executable functional/integration checks: FT-01, FT-02, and FT-03. Run the suite to determine actual pass/fail results. FR-02 (rental listing filtering) is not tested because the filtering interface is not implemented in this repository snapshot. These tests do not demonstrate that FR-02 is complete.

The test-case descriptions should be integrated into the team specification, which has a four-page limit unless justified.
