# Data dictionary

This dictionary describes the frozen RentCast snapshot `ucsd_rentals_2026-11-16_102139_PT` and the Member A analysis derived from it. The snapshot contains **2,690 listings and 20 columns in `listings`**, confirmed by both `schema.json` and SQLite `PRAGMA table_info`. The processed `analysis_listings` table preserves those 20 columns and adds **23 derived columns**, for 43 columns total.

One row represents one provider listing ID, not a verified household, building, or available entire rental unit. Advertised rent may have differing room, unit, or floorplan meanings that have not been independently verified. The capture ran on November 16, 2026, 10:21:39–10:23:19 America/Los_Angeles; it is a sequential API capture rather than an atomic market snapshot.

## Tables, keys, and storage

| Database/table | Grain and fields | Key and relationship |
| --- | --- | --- |
| Frozen `rentals.sqlite`: `listings` | 2,690 rows; the 20 selected fields below. | `id TEXT PRIMARY KEY`. Each observed ID is present and unique. |
| Frozen `rentals.sqlite`: `raw_listings` | 2,690 rows; complete original provider record in `record_json`. | `id TEXT PRIMARY KEY`, corresponding to `listings.id`; `record_json TEXT NOT NULL`. The relationship is logical, without a declared SQL foreign key. |
| Frozen `rentals.sqlite`: `snapshot_metadata` | 21 key/value rows describing collection, query, requests, counts, and finalization. These are metadata entries, not 21 listing columns. | `key TEXT PRIMARY KEY`; `value_json TEXT NOT NULL` stores a JSON-encoded value, which may be a string, number, Boolean, object, or array. |
| Processed `analysis.sqlite`: `analysis_listings` | 2,690 rows; 20 source-table columns plus 23 Member A derived columns. | `id` is preserved and covered by unique index `idx_analysis_id`. Pandas `to_sql(index=False)` creates the table without declaring a SQL primary key or `NOT NULL` on `id`. A unique index prevents duplicate non-null IDs but is not a primary-key/nonnull declaration. `load_snapshot` separately rejects null or duplicate IDs before processing. |

The frozen database is under `data/frozen/ucsd_rentals_2026-11-16_102139_PT/`; the regenerated database is under `data/processed/member_a/`. The JSON export `analysis_listings.json` represents the same processed records, with missing values written as JSON `null`.

In the tables below, **nulls** means observed SQL NULL or pandas missing values in this snapshot. It does not promise an SQL `NOT NULL` constraint. The source `listings` columns have no explicit `NOT NULL` declaration. IDs are checked by the pipeline, and derived flags are populated for every row. Numeric source fields retain their original values; numeric conversion creates separate analysis columns. No rows are dropped and no missing values are imputed.

## Frozen `listings` fields

“Provider” identifies selected fields copied from RentCast. “Collection” and “snapshot-derived” identify fields added during the original freeze. All 20 are source columns for the Member A pipeline and remain unchanged there.

| Field | Origin | SQLite type / units | Nulls / nullable meaning | Definition |
| --- | --- | --- | --- | --- |
| `id` | Provider | `TEXT`; identifier | 0; must be present for processing | Stable provider listing identifier used for joins and uniqueness checks. Do not infer independent housing units from distinct IDs. |
| `formattedAddress` | Provider | `TEXT`; address | 0; source may be missing in other captures | Provider-formatted listing address, potentially including a unit or room designation. Not an independently standardized or verified address. |
| `city` | Provider | `TEXT`; city name | 0; nullable in storage | Provider city label. It is not a neighborhood classification. |
| `state` | Provider | `TEXT`; state abbreviation | 0; nullable in storage | Provider state label; all observed records are `CA`. |
| `zipCode` | Provider | `TEXT`; postal code | 0; nullable in storage | Postal code retained as text, not a numeric quantity. |
| `latitude` | Provider | `REAL`; decimal degrees | 0; nullable in storage | Provider latitude. Positive values indicate north. Used for straight-line distance and coordinate grouping. |
| `longitude` | Provider | `REAL`; decimal degrees | 0; nullable in storage | Provider longitude. Negative values indicate west. Used for straight-line distance and coordinate grouping. |
| `propertyType` | Provider | `TEXT`; category | 0; nullable in storage | Provider property category, such as Apartment or Multi-Family. Does not independently establish the rental's occupancy or pricing basis. |
| `bedrooms` | Provider | `REAL`; bedroom count | 0; null would mean unknown | Provider bedroom count; 0 is treated as studio. Stored as numeric, even when observed values are integers. |
| `bathrooms` | Provider | `REAL`; bathroom count | 0; null would mean unknown | Provider bathroom count; fractional values are retained. |
| `squareFootage` | Provider | `REAL`; square feet | 85; missing area is unknown | Provider living area. Missing area remains missing and does not remove the listing from monthly-rent analysis. |
| `price` | Provider | `REAL`; USD/month | 0; nullable in storage | Advertised monthly listing rent. It is not verified paid rent or total housing cost; utilities, fees, concessions, furnishing, lease terms, and room-versus-entire-unit differences are not normalized. |
| `status` | Provider | `TEXT`; category | 0; nullable in storage | Provider listing status. All observed rows are `Active`, which is a provider assertion rather than independently verified availability. |
| `listedDate` | Provider | `TEXT`; ISO timestamp | 0; nullable in storage | Provider-reported listing timestamp. It is not the project's collection timestamp. |
| `lastSeenDate` | Provider | `TEXT`; ISO timestamp | 0; nullable in storage | Timestamp when the provider last saw the listing. It is not collection time or independent availability verification. |
| `daysOnMarket` | Provider | `REAL`; days | 0; nullable in storage | Provider-reported days on market, retained as supplied rather than recomputed from dates. |
| `sourcePageOffset` | Collection | `INTEGER`; API row offset | 0; populated during collection | Offset for the response page from which the retained record was obtained. It supports provenance and is not a listing feature. |
| `sourceRequestedAtUtc` | Collection | `TEXT`; ISO UTC timestamp | 0; populated during collection | Time the originating API page request was made. It describes collection, not listing freshness. |
| `distanceToCampusMiles` | Snapshot-derived | `REAL`; miles | 0; would be unavailable without usable coordinates | Haversine straight-line distance to the fixed UCSD reference point `(32.8801, -117.2340)`. It is not walking/driving distance, travel time, or distance to a particular classroom. |
| `advertisedRentPerSqft` | Snapshot-derived | `REAL`; USD/sqft/month | 85; missing when area is unusable | Frozen collector's `price / squareFootage`, rounded to six decimal places, when price and area are numeric and area is positive; otherwise null. Member A recomputes its own version using stricter validity checks. |

## Member A derived fields

These fields are appended by `prepare_data` in `src/ucsd_rentals/data.py`. Numeric values are stored as SQLite `REAL`, counts as `INTEGER`, and Boolean flags as `INTEGER` (`1`/`0`). Labels are stored as `TEXT`; the two ordered pandas categories are converted to strings before export. Ordering must therefore be explicitly supplied again when reading SQLite or JSON for a plot.

| Field | Logical type / units | Nulls / nullable meaning | Definition |
| --- | --- | --- | --- |
| `monthly_rent_usd` | Numeric / USD/month | 0; missing if source rent is missing or cannot be converted | Numeric conversion of `price`. Conversion does not itself remove nonpositive or infinite numbers; `rent_valid` records usability. |
| `area_sqft` | Numeric / sqft | 85; missing if source area is missing or cannot be converted | Numeric conversion of `squareFootage`, without imputation. |
| `bedroom_count` | Numeric / bedrooms | 0; missing if source count is missing or cannot be converted | Numeric conversion of `bedrooms`; 0 remains studio. |
| `bathroom_count` | Numeric / bathrooms | 0; missing if source count is missing or cannot be converted | Numeric conversion of `bathrooms`; fractional counts remain unchanged. |
| `rent_valid` | Boolean | 0; always populated | True exactly when `monthly_rent_usd` is finite and strictly greater than zero. |
| `area_valid` | Boolean | 0; always populated | True exactly when `area_sqft` is finite and strictly greater than zero. |
| `rent_per_sqft_usd` | Numeric / USD/sqft/month | 85; missing if rent or area is invalid | `monthly_rent_usd / area_sqft` only when both values are finite and strictly positive. Calculated without the frozen field's six-decimal rounding. |
| `area_missing` | Boolean | 0; always populated | True when the **original** `squareFootage` is missing. A malformed nonmissing value is classified by the next flag instead. |
| `area_invalid_nonmissing` | Boolean | 0; always populated | True when original area is nonmissing but its numeric analysis value is unusable: unparseable, nonfinite, zero, or negative. |
| `coordinates_valid` | Boolean | 0; always populated | True when converted latitude and longitude are finite and within `[-90, 90]` and `[-180, 180]`, respectively. This is a numerical check, not geocoding verification. |
| `distance_miles` | Numeric / miles | 0; missing for invalid coordinates | Recomputed Haversine straight-line distance to `(32.8801, -117.2340)`, with Earth radius 3,958.7613 miles. |
| `within_10_miles` | Boolean | 0; always populated | True when `distance_miles` lies in the inclusive interval `[0, 10]`. Missing distance gives False. |
| `eligible_for_rent_analysis` | Boolean | 0; always populated | `rent_valid` AND `within_10_miles` AND provider `status == 'Active'`. This checks analysis eligibility, not whole-unit pricing or availability. All 2,690 frozen rows qualify. |
| `eligible_for_area_analysis` | Boolean | 0; always populated | `eligible_for_rent_analysis` AND `area_valid`. Exactly 2,605 frozen rows qualify; the other 85 remain in the processed table and monthly-rent analysis. |
| `distance_band` | Ordered category → text / miles | 0; missing if distance is outside `[0, 10]` or missing | Ordered labels `0-1 mi`, `1-2 mi`, `2-3 mi`, `3-5 mi`, `5-10 mi`. Intervals are `[0, 1]`, `(1, 2]`, `(2, 3]`, `(3, 5]`, `(5, 10]`. |
| `bedroom_label` | Text / label | 0; unknown becomes a text label | Detailed bedroom label: missing → `Unknown`, zero → `Studio`, integer count → e.g. `1 BR`; other numeric values are represented as text. This label does not independently validate bedroom counts. |
| `bedroom_plot_group` | Ordered category → text / label | 0; invalid or missing counts become `Unknown` | Ordered categories `Studio`, `1 BR`, `2 BR`, `3 BR`, `4+ BR`, `Unknown`. Finite nonnegative integer counts are required; 4 or more bedrooms are combined. Negative, noninteger, missing, or nonfinite counts map to `Unknown`. The exact count remains in `bedroom_count`. |
| `rent_iqr_review` | Boolean | 0; always populated | True for eligible listings whose rent is strictly below `Q1 − 1.5 × IQR` or above `Q3 + 1.5 × IQR`, calculated within the exact `bedroom_count` group. Requires at least 4 eligible records in that group. Quartiles use pandas linear interpolation. This is a review flag, not a deletion rule. |
| `multifamily_review` | Boolean | 0; always populated | True when source `propertyType` equals `Multi-Family`. Signals a category to inspect; it does not prove a listing represents a whole building. |
| `room_wording_review` | Boolean | 0; always populated | Case-insensitive whole-word search for `rm`, `room`, or `bedroom` in `formattedAddress`; missing address gives False. Flags possible room wording only. True does not establish room rental, and False does not establish an entire unit. |
| `area_extreme_review` | Boolean | 0; always populated | True for valid area strictly below 250 sqft or strictly above 5,000 sqft. The boundary values 250 and 5,000 are not flagged. These are review thresholds, not evidence of error. |
| `long_market_review` | Boolean | 0; always populated | True when numeric-converted `daysOnMarket` is strictly greater than 365; missing/unparseable values give False. No listing is removed because of this flag. |
| `coordinate_cluster_size` | Integer / listings | 0; at least 1 for each row | Number of rows sharing the exact original `(latitude, longitude)` pair. Grouping includes missing coordinates if present. A coordinate cluster is a coarse proxy, not a verified building or duplicate listing. |

Review flags can overlap and are never subtracted from the primary sample. In this frozen dataset, `rent_iqr_review` marks 219 rows, `multifamily_review` 6, `room_wording_review` 2, `area_extreme_review` 12, and `long_market_review` 346. These counts describe checks, not confirmed errors.

## Summary-table fields

The JSON summary tables in `results/member_a/` use `group_summary`. Their first column names the chosen grouping field; it is followed by the fields below. Numeric statistics use only finite, strictly positive values of the requested measure. Default measure is monthly advertised rent; the rent-per-square-foot table uses `rent_per_sqft_usd`.

| Field | Type / units | Nullability and meaning |
| --- | --- | --- |
| Grouping column | Same meaning as input grouping field | Observed group label. Missing grouping values form a group when present; unused categorical groups are not emitted. |
| `n_records` | Integer / listings | Nonmissing; number of rows supplied to this group before excluding unusable measure values. |
| `n_valid` | Integer / listings | Nonmissing; finite, strictly positive measure count used for all statistics. |
| `n_missing` | Integer / listings | Nonmissing; `n_records - n_valid`. Despite its name, includes nonfinite and nonpositive values as well as missing/unparseable values. It is not necessarily the SQL NULL count. |
| `median` | Numeric / measure units | Null for a group with no valid values; otherwise the ordinary median, averaging the two middle values for an even count. |
| `mean` | Numeric / measure units | Null for a group with no valid values; otherwise arithmetic mean. |
| `q1` | Numeric / measure units | Null for a group with no valid values; otherwise 25th percentile using linear interpolation. |
| `q3` | Numeric / measure units | Null for a group with no valid values; otherwise 75th percentile using linear interpolation. |
| `min` | Numeric / measure units | Null for a group with no valid values; otherwise smallest valid value. |
| `max` | Numeric / measure units | Null for a group with no valid values; otherwise largest valid value. |

Summary counts refer to the frame supplied to the function, which may already be restricted to eligible listings or a bedroom subgroup. They should not automatically be interpreted as counts from all 2,690 source records.

## Interpretation and provenance

The data describe this RentCast query result within a 10-mile straight-line radius, not every rental in the UCSD market. Source timestamps, addresses, property categories, and prices remain provider assertions. Shared coordinates and multiple listings from a building can reduce statistical independence. Distances are not commute measures; price differences are descriptive and do not establish causal effects of distance or bedrooms.

The dictionary was checked against the committed `schema.json`, read-only SQLite schema/data queries, `src/ucsd_rentals/data.py`, and the export code in `scripts/run_member_a.py`. Preserve the frozen source files and regenerate derived outputs with `python scripts/run_member_a.py`.
