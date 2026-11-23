## 3. Data Models

### 3.1 Data Description

We use a frozen RentCast rental-listing snapshot collected on November 16, 2026, from 10:21:39 to 10:23:19 Pacific time. It contains **2,690 unique listing IDs** with provider status `Active`, within a **10-mile straight-line radius** of the UCSD reference point (32.8801, -117.2340). Each row represents one rental advertisement. The data support comparisons of advertised rent by bedroom count, property type, ZIP code, floor area, and distance.

### 3.2 Schema and Storage

The frozen SQLite database, `rentals.sqlite`, contains three tables. `listings` has 2,690 rows and 20 columns, with `id` as its primary key. `raw_listings` stores each complete provider record as JSON, matched to `listings` by ID. `snapshot_metadata` stores collection and verification information as key/JSON-value pairs.

| Fields in `listings` | Type and meaning |
| --- | --- |
| `id` | Text primary key identifying the advertisement. |
| `formattedAddress`, `city`, `state`, `zipCode` | Text location labels, with ZIP codes retained as text. |
| `latitude`, `longitude` | Numeric geographic coordinates in decimal degrees. |
| `propertyType`, `bedrooms`, `bathrooms` | Text property category and numeric room counts. Zero bedrooms indicates a studio. |
| `price`, `squareFootage` | Numeric advertised monthly rent in USD and reported floor area in square feet. Missing area is stored as null. |
| `status`, `listedDate`, `lastSeenDate`, `daysOnMarket` | Text provider status, listing and last-seen timestamps, and numeric market duration in days. |
| `sourcePageOffset`, `sourceRequestedAtUtc` | Integer API page offset and text UTC request timestamp for provenance. |
| `distanceToCampusMiles`, `advertisedRentPerSqft` | Numeric straight-line miles and USD per square foot per month, derived during collection. |

The pipeline reads the frozen database in read-only mode and verifies its SHA-256 checksums and database integrity. It retains all source rows and columns, then adds 23 analysis fields, producing a **2,690-row, 43-column** `analysis_listings` table in `data/processed/member_a/analysis.sqlite`, with a unique index on `id`. Added fields include numeric analysis columns, recomputed distance and unit rent, grouping labels, eligibility flags, and review flags. Unit rent is calculated as rent divided by valid positive area. A JSON export provides the same records. Summary tables and figures are stored under `results/member_a/`. The committed snapshot allows offline regeneration. Full field definitions are in [the data dictionary](data_dictionary.md).

## 4. Assumptions & Constraints

We interpret `price` as monthly advertised USD and `squareFootage` as reported square feet. Fees, concessions, furnishing, and lease duration may differ across advertisements. The pricing basis of rooms, entire units, and floorplans remains unverified. `Active` and `lastSeenDate` are provider assertions, so current availability requires independent confirmation.

All **2,690** records qualify for monthly-rent analysis. **85** lack floor area and remain eligible for rent comparisons and filtering. Area-based calculations use the **2,605** records with valid area, with valid and excluded counts reported. Missing area remains null. Unusual values are retained with review flags, and distinct IDs sharing coordinates are preserved because they may describe different units. Such records may be statistically dependent.

Results describe the provider's coverage at collection time. A single snapshot limits analysis of market trends and broader representativeness. Distance uses a fixed campus reference point and the Haversine formula, which measures straight-line separation. Commute times require additional data. Differences in property mix and listing conditions limit causal interpretations of rent comparisons.
