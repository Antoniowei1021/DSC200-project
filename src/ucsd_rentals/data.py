"""Member A: transparent, non-destructive data preparation and summaries."""

import math
from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd

CAMPUS = (32.8801, -117.2340)
DISTANCE_LABELS = ["0-1 mi", "1-2 mi", "2-3 mi", "3-5 mi", "5-10 mi"]
BEDROOM_PLOT_GROUPS = ["Studio", "1 BR", "2 BR", "3 BR", "4+ BR", "Unknown"]


def unit_rent(price, area):
    """Return advertised USD/sqft, or None if rent or area is unusable."""
    try:
        price, area = float(price), float(area)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(price) or not math.isfinite(area) or price <= 0 or area <= 0:
        return None
    return price / area


def load_snapshot(path):
    """Open the baseline read-only; preserve source columns and stable ID order."""
    path = Path(path).resolve()
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
        frame = pd.read_sql_query("SELECT * FROM listings ORDER BY id", db)
    if frame["id"].isna().any() or frame["id"].duplicated().any():
        raise ValueError(
            "Snapshot IDs must be present and unique; do not silently drop records."
        )
    return frame


def _bedroom_label(count):
    """Keep the exact source bedroom count in the detailed analysis label."""
    if pd.isna(count):
        return "Unknown"
    if count == 0:
        return "Studio"
    if float(count).is_integer():
        return f"{int(count)} BR"
    return str(count)


def _bedroom_plot_group(count):
    """Combine valid counts of four or more bedrooms for stable plot groups."""
    if pd.isna(count) or not math.isfinite(count):
        return "Unknown"
    if count < 0 or not float(count).is_integer():
        return "Unknown"
    if count == 0:
        return "Studio"
    if count >= 4:
        return "4+ BR"
    return f"{int(count)} BR"


def prepare_data(source):
    """Add numeric analysis columns and flags without dropping or imputing rows."""
    frame = source.copy(deep=True)
    numeric_columns = [
        ("price", "monthly_rent_usd"),
        ("squareFootage", "area_sqft"),
        ("bedrooms", "bedroom_count"),
        ("bathrooms", "bathroom_count"),
    ]
    for source_name, name in numeric_columns:
        frame[name] = pd.to_numeric(frame[source_name], errors="coerce")

    frame["rent_valid"] = np.isfinite(frame["monthly_rent_usd"]) & (
        frame["monthly_rent_usd"] > 0
    )
    frame["area_valid"] = np.isfinite(frame["area_sqft"]) & (
        frame["area_sqft"] > 0
    )
    frame["rent_per_sqft_usd"] = [
        unit_rent(price, area)
        for price, area in zip(frame["monthly_rent_usd"], frame["area_sqft"])
    ]
    # A malformed source value is invalid, not an originally missing value.
    frame["area_missing"] = frame["squareFootage"].isna()
    frame["area_invalid_nonmissing"] = (
        ~frame["area_valid"] & ~frame["area_missing"]
    )

    lat = pd.to_numeric(frame["latitude"], errors="coerce")
    lon = pd.to_numeric(frame["longitude"], errors="coerce")
    frame["coordinates_valid"] = (
        np.isfinite(lat)
        & np.isfinite(lon)
        & lat.between(-90, 90)
        & lon.between(-180, 180)
    )
    campus_lat, campus_lon = np.radians(CAMPUS)
    listing_lat, listing_lon = np.radians(lat), np.radians(lon)
    hav = (
        np.sin((listing_lat - campus_lat) / 2) ** 2
        + np.cos(campus_lat)
        * np.cos(listing_lat)
        * np.sin((listing_lon - campus_lon) / 2) ** 2
    )
    frame["distance_miles"] = (
        3958.7613 * 2 * np.arcsin(np.sqrt(np.clip(hav, 0, 1)))
    ).where(frame["coordinates_valid"])
    frame["within_10_miles"] = frame["distance_miles"].between(0, 10)
    frame["eligible_for_rent_analysis"] = (
        frame["rent_valid"]
        & frame["within_10_miles"]
        & frame["status"].eq("Active")
    )
    frame["eligible_for_area_analysis"] = (
        frame["eligible_for_rent_analysis"] & frame["area_valid"]
    )
    frame["distance_band"] = pd.cut(
        frame["distance_miles"],
        [0, 1, 2, 3, 5, 10],
        labels=DISTANCE_LABELS,
        include_lowest=True,
        right=True,
    )
    frame["bedroom_label"] = frame["bedroom_count"].map(_bedroom_label)
    frame["bedroom_plot_group"] = pd.Categorical(
        frame["bedroom_count"].map(_bedroom_plot_group),
        categories=BEDROOM_PLOT_GROUPS,
        ordered=True,
    )

    # Statistical review flag, not a deletion rule; stratify by bedroom count.
    valid = frame.loc[frame["eligible_for_rent_analysis"]]
    q1 = valid.groupby("bedroom_count")["monthly_rent_usd"].quantile(0.25)
    q3 = valid.groupby("bedroom_count")["monthly_rent_usd"].quantile(0.75)
    sizes = valid.groupby("bedroom_count").size()
    lo = frame["bedroom_count"].map(q1 - 1.5 * (q3 - q1))
    hi = frame["bedroom_count"].map(q3 + 1.5 * (q3 - q1))
    frame["rent_iqr_review"] = (
        frame["eligible_for_rent_analysis"]
        & frame["bedroom_count"].map(sizes).ge(4)
        & (
            (frame["monthly_rent_usd"] < lo)
            | (frame["monthly_rent_usd"] > hi)
        )
    )
    frame["multifamily_review"] = frame["propertyType"].eq("Multi-Family")
    frame["room_wording_review"] = (
        frame["formattedAddress"]
        .astype("string")
        .str.contains(r"\b(?:rm|room|bedroom)\b", case=False, na=False)
        .astype(bool)
    )
    frame["area_extreme_review"] = frame["area_valid"] & (
        (frame["area_sqft"] < 250) | (frame["area_sqft"] > 5000)
    )
    frame["long_market_review"] = pd.to_numeric(
        frame["daysOnMarket"], errors="coerce"
    ).gt(365)
    frame["coordinate_cluster_size"] = frame.groupby(
        ["latitude", "longitude"], dropna=False
    )["id"].transform("size")

    assert len(frame) == len(source) and frame["id"].tolist() == source["id"].tolist()
    return frame


def group_summary(frame, group_col, value_col="monthly_rent_usd"):
    """All groups observed in frame; finite positive amounts only in statistics.

    n_records is the total group size, n_valid the statistical denominator,
    and n_missing the excluded amount count (missing, nonfinite or nonpositive).
    Quartiles use pandas' linear interpolation; median is the ordinary median.
    """
    records = []
    for label, group in frame.groupby(
        group_col, dropna=False, observed=True, sort=True
    ):
        values = pd.to_numeric(group[value_col], errors="coerce")
        valid = values.loc[np.isfinite(values) & (values > 0)]
        record = {
            group_col: label,
            "n_records": len(group),
            "n_valid": len(valid),
            "n_missing": len(group) - len(valid),
        }
        statistics = [
            ("median", lambda: valid.median()),
            ("mean", lambda: valid.mean()),
            ("q1", lambda: valid.quantile(0.25)),
            ("q3", lambda: valid.quantile(0.75)),
            ("min", lambda: valid.min()),
            ("max", lambda: valid.max()),
        ]
        for name, calculate in statistics:
            record[name] = float(calculate()) if len(valid) else None
        records.append(record)
    return pd.DataFrame(
        records,
        columns=[
            group_col,
            "n_records",
            "n_valid",
            "n_missing",
            "median",
            "mean",
            "q1",
            "q3",
            "min",
            "max",
        ],
    )
