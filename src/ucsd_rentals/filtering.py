"""Member B: filtering for the UCSD rental-listing analysis (FR-02).

This module consumes Member A's `analysis_listings` DataFrame. It never modifies
its input, does not access the network, and never writes to the frozen snapshot.
"""

import math
from numbers import Integral, Real

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = (
    "id",
    "monthly_rent_usd",
    "bedroom_count",
    "distance_miles",
    "eligible_for_rent_analysis",
)
MAX_DATASET_RADIUS_MILES = 10.0


def _nonnegative_number(value, name):
    """Validate an optional finite, nonnegative numeric filter value."""
    if value is None:
        return None
    # bool is a subclass of int, but is not a meaningful user budget/distance.
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite, nonnegative number or None")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError(f"{name} must be a finite, nonnegative number or None")
    return result


def _bedroom_count(value):
    """Accept a nonnegative integer, including 0 for a studio, or None."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, Integral) or value < 0:
        raise ValueError("bedrooms must be a nonnegative integer or None")
    return int(value)


def filter_listings(
    listings,
    max_monthly_rent=None,
    bedrooms=None,
    max_distance_miles=None,
):
    """Return all rental listings matching the supplied optional filters.

    - Conditions are combined with AND.
    - Monthly rent and straight-line distance use inclusive upper bounds.
    - Bedrooms are matched exactly; zero denotes a studio.
    - Missing criteria impose no extra restriction.
    - The underlying dataset is restricted to eligible active rental listings
      within the project's 10-mile UCSD radius, even when distance is omitted.
    - Missing floor area does not remove an otherwise eligible listing.
    - IDs, all columns, and original row order are preserved; input is untouched.

    Parameters are Python/NumPy numeric values or None, *not* strings or bools.
    An upper distance limit over 10 miles is allowed but cannot expand the
    frozen dataset beyond its existing 10-mile geographic scope.
    """
    rent_limit = _nonnegative_number(max_monthly_rent, "max_monthly_rent")
    bedroom_limit = _bedroom_count(bedrooms)
    distance_limit = _nonnegative_number(max_distance_miles, "max_distance_miles")

    if not isinstance(listings, pd.DataFrame):
        raise TypeError("listings must be a pandas DataFrame")
    missing = sorted(set(REQUIRED_COLUMNS) - set(listings.columns))
    if missing:
        raise ValueError(f"Missing required analysis columns: {', '.join(missing)}")
    if listings["id"].isna().any() or listings["id"].duplicated().any():
        raise ValueError("Listing IDs must be present and unique")

    rents = pd.to_numeric(listings["monthly_rent_usd"], errors="coerce")
    distances = pd.to_numeric(listings["distance_miles"], errors="coerce")
    eligible = listings["eligible_for_rent_analysis"].eq(1).fillna(False)

    # Filter invalid or out-of-scope rows even if a mistakenly set flag says 1.
    mask = (
        eligible
        & np.isfinite(rents)
        & rents.gt(0)
        & np.isfinite(distances)
        & distances.between(0, MAX_DATASET_RADIUS_MILES, inclusive="both")
    )
    if rent_limit is not None:
        mask &= rents.le(rent_limit)
    if bedroom_limit is not None:
        bedroom_values = pd.to_numeric(listings["bedroom_count"], errors="coerce")
        mask &= bedroom_values.eq(bedroom_limit)
    if distance_limit is not None:
        mask &= distances.le(distance_limit)

    return listings.loc[mask].copy()
