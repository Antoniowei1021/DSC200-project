# DSC200-project

Rental price analysis near UC San Diego for DSC 200.

## Frozen dataset

Use the committed snapshot for project analysis; an API key is **not required**.

| Item | Value |
| --- | --- |
| Source | RentCast rental listings API |
| Collection window | November 16, 2026, 10:21:39-10:23:19 America/Los_Angeles (UTC-08:00) |
| Campus reference | Latitude 32.8801, longitude -117.2340 |
| Search | 10-mile straight-line radius, `status=Active` |
| Frozen records | 2,690 unique IDs and formatted addresses |
| Missing floor area | 85 records; retained without imputation |
| Missing rent, bedrooms, bathrooms, coordinates | 0 records |
| API requests | 6 pages plus 1 overlapping boundary-repair request |

Snapshot: [`data/frozen/ucsd_rentals_2026-11-16_102139_PT/`](data/frozen/ucsd_rentals_2026-11-16_102139_PT/).

- `rentals.sqlite`: SQLite database with `listings`, `raw_listings`, and `snapshot_metadata` tables.
- `listings.json`: analysis fields, derived distance and rent per square foot, and source-page provenance.
- `raw_listings.json` and `pages/`: complete provider records and original API responses.
- `schema.json`, `quality_report.json`, and `manifest.json`: field definitions, quality checks, and collection provenance.
- `SHA256SUMS`: checksums for every snapshot file except the checksum list itself.

The snapshot is committed byte-for-byte as collected and finalized. Its original collection notes are preserved; this repository intentionally tracks that one frozen version. Write cleaned datasets and analysis outputs elsewhere. Git does not preserve read-only file permissions, so use the checksums and read-only database access to protect the baseline.

## Verify and read the data

Python 3.9 or later is sufficient for the included scripts; they use the standard library.

From the repository root, verify the checksums, database integrity, record count, and geographic bounds:

```bash
python3 scripts/verify_snapshot.py
```

Read the database without allowing modifications:

```python
from pathlib import Path
import sqlite3

path = Path("data/frozen/ucsd_rentals_2026-11-16_102139_PT/rentals.sqlite").resolve()
with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as connection:
    rows = connection.execute(
        "SELECT id, price, bedrooms, bathrooms, squareFootage, distanceToCampusMiles "
        "FROM listings"
    ).fetchall()
```

## Collection and completeness

The initial six pages returned 2,690 rows but only 2,689 unique IDs. A tied `lastSeenDate` across the offset-1,000 boundary caused one duplicate and one missing listing. An overlapping request at offset 990 with limit 20 recovered the missing listing. Duplicate records were checked for identical contents before deduplication. The final 2,690 unique records match the total reported by all seven responses.

All unique records were retained, including missing areas and unusual prices. Different apartments in one building may share coordinates and are not necessarily independent statistical observations.

This is the complete **RentCast query result during the recorded collection window**, not all rental listings in the market or an atomic provider snapshot. `Active` and `lastSeenDate` are provider assertions. Advertised rents have not been adjusted for fees, lease terms, furniture, concessions, or room-versus-entire-unit differences.

## Collecting a new version (optional)

The project should use the existing frozen data. Only run collection when intentionally requesting a new version and after checking the account's API allowance. Set `RENTCAST_API_KEY` in your local process environment; never put a real key in source code, commits, issues, or notebooks.

```bash
python3 scripts/freeze_rentcast.py
```

The collector creates a new timestamped directory, saves each page, and stops if completeness checks fail. It never overwrites the committed snapshot and makes no automatic retries. If a boundary problem is found, inspect the saved pages before using `repair_rentcast_page.py` with a targeted offset and limit, then run `finalize_rentcast_pages.py` on that new directory. The finalizer is preserved from this collection and its narrative describes the specific November 16 repair; adapt that narrative before using it for a different collection.

## Data rights and AI assistance

The dataset is third-party RentCast API data, not data owned or relicensed as open source by this project. See [DATA_LICENSE.txt](DATA_LICENSE.txt) and the [RentCast API terms](https://www.rentcast.io/terms-api).

Codex assisted with source research, collection scripts, pagination diagnosis, dataset validation, and this documentation. These contributions are recorded here for course transparency. Team members should review the code and results and follow the course's full AI disclosure requirements. The required personal reflection is not included here and must be written by the students themselves.
