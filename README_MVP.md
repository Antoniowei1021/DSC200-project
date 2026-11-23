# DSC 200 — Member B Filtering MVP

The folder structure in this archive matches the existing GitHub repository:
`https://github.com/Antoniowei1021/DSC200-project`.

Copy `src/`, `scripts/`, `tests/`, and `docs/` over the corresponding repo folders.
These files are **new additions**, and should not overwrite existing Member A code.

The implementation and usage guide is in `docs/member_b_filtering_mvp.md`.

The MVP filters the existing processed `analysis_listings` data by optional
monthly rent (inclusive), exact bedroom count, and UCSD straight-line distance
(inclusive), within the 10-mile snapshot. It exports a CSV with listing IDs.

From your repository root, after installing dependencies:

```bash
python scripts/run_member_a.py
PYTHONPATH=src python -m unittest tests.test_filtering -v
python scripts/filter_listings.py --max-rent 2500 --bedrooms 2 --max-distance 5
```

The scripts do not make network requests or alter frozen datasets. The files
were generated and tested outside GitHub; they have not been pushed to main.
