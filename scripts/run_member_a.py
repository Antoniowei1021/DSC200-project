"""Build member A's derived database, descriptive tables and figures offline."""

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import sqlite3
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ucsd_rentals.data import (
    DISTANCE_LABELS,
    group_summary,
    load_snapshot,
    prepare_data,
)
from verify_snapshot import main as verify_snapshot

SNAPSHOT = ROOT / "data/frozen/ucsd_rentals_2026-11-16_102139_PT"


def dump(path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    )


def records(frame):
    return json.loads(frame.to_json(orient="records", double_precision=12))


def hashes(folder):
    return {
        str(path.relative_to(folder)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(folder.rglob("*"))
        if path.is_file()
    }


def plots(frame, output):
    # Keep matplotlib caches out of the repository and data baseline.
    os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "tmp/matplotlib"))
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FixedLocator, NullFormatter, StrMethodFormatter

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "savefig.dpi": 180,
            "figure.facecolor": "white",
        }
    )

    counts = frame.groupby("bedroom_plot_group", observed=True).size()
    labels = counts.index.astype(str).tolist()
    groups = [
        frame.loc[
            frame["bedroom_plot_group"] == bedroom_group, "monthly_rent_usd"
        ].to_numpy()
        for bedroom_group in counts.index
    ]
    figure, axis = plt.subplots(figsize=(10, 6.3), layout="constrained")
    boxplot = axis.boxplot(
        groups,
        tick_labels=[
            f"{label}\nn={count:,}" for label, count in zip(labels, counts)
        ],
        patch_artist=True,
        showfliers=True,
        flierprops={"markersize": 3, "alpha": 0.4},
        medianprops={"color": "#111111", "linewidth": 1.7},
    )
    for patch in boxplot["boxes"]:
        patch.set_facecolor("#92B6C6")

    axis.set_yscale("log")
    axis.yaxis.set_major_locator(
        FixedLocator([1000, 2000, 3000, 5000, 10000, 20000])
    )
    axis.yaxis.set_major_formatter(StrMethodFormatter("${x:,.0f}"))
    axis.yaxis.set_minor_formatter(NullFormatter())
    axis.set_ylabel("Advertised monthly rent (USD; logarithmic scale)")
    axis.set_title(
        "Advertised monthly rent by bedroom count", loc="left", weight="bold"
    )
    axis.grid(axis="y", alpha=0.18)
    axis.set_axisbelow(True)
    figure.supxlabel(
        "RentCast snapshot: Nov 16, 2026 | UCSD reference point, 10-mile radius\n"
        "4+ BR combines 4-7 bedrooms. Dots lie outside 1.5 IQR whiskers; "
        "all records retained.",
        fontsize=9,
    )
    figure.savefig(output / "rent_by_bedrooms.png")
    figure.savefig(output / "rent_by_bedrooms.pdf")
    plt.close(figure)

    # Compare 1/2 BR listings to reduce (not eliminate) unit-mix differences.
    figure, axis = plt.subplots(figsize=(10, 6.3), layout="constrained")
    series_styles = [
        (1, "#1F5A7A", "o", -0.09),
        (2, "#B65B26", "s", 0.09),
    ]
    for bedroom_count, color, marker, shift in series_styles:
        bedroom_listings = frame.loc[frame["bedroom_count"] == bedroom_count]
        summary = group_summary(bedroom_listings, "distance_band").set_index(
            "distance_band"
        )
        for band_index, band in enumerate(DISTANCE_LABELS):
            if band not in summary.index:
                continue
            band_summary = summary.loc[band]
            x_position = band_index + shift
            axis.errorbar(
                x_position,
                band_summary["median"],
                yerr=[
                    [band_summary["median"] - band_summary["q1"]],
                    [band_summary["q3"] - band_summary["median"]],
                ],
                fmt=marker,
                color=color,
                capsize=5,
                markersize=7,
                label=(
                    f"{bedroom_count} BR: median and IQR"
                    if band_index == 0
                    else None
                ),
            )
            axis.annotate(
                f"n={int(band_summary['n_valid'])}",
                (x_position, band_summary["q3"]),
                xytext=(0, 7 if bedroom_count == 1 else 18),
                textcoords="offset points",
                ha="center",
                fontsize=8,
                color=color,
            )

    axis.set_xticks(range(len(DISTANCE_LABELS)), DISTANCE_LABELS)
    axis.set_ylabel("Advertised monthly rent (USD)")
    axis.yaxis.set_major_formatter(StrMethodFormatter("${x:,.0f}"))
    axis.set_title(
        "Rent by distance for one- and two-bedroom listings",
        loc="left",
        weight="bold",
    )
    axis.legend(frameon=False, loc="upper right")
    axis.grid(axis="y", alpha=0.18)
    axis.set_axisbelow(True)
    axis.margins(y=0.25)
    figure.supxlabel(
        "Straight-line distance; bins include their right endpoint | "
        "RentCast, Nov 16, 2026\n"
        "Bars show the middle 50% of listings, not confidence intervals. "
        "No causal effect is estimated.",
        fontsize=9,
    )
    figure.savefig(output / "rent_by_distance.png")
    figure.savefig(output / "rent_by_distance.pdf")
    plt.close(figure)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "results/member_a")
    parser.add_argument(
        "--processed", type=Path, default=ROOT / "data/processed/member_a"
    )
    args = parser.parse_args()
    for target in [args.output, args.processed]:
        if target.resolve() == SNAPSHOT or SNAPSHOT in target.resolve().parents:
            parser.error("Output cannot be inside the frozen snapshot.")
        target.mkdir(parents=True, exist_ok=True)

    source_hashes_before = hashes(SNAPSHOT)
    verify_snapshot()
    source = load_snapshot(SNAPSHOT / "rentals.sqlite")
    frame = prepare_data(source)
    rent_eligible = frame.loc[frame["eligible_for_rent_analysis"]]
    area_eligible = frame.loc[frame["eligible_for_area_analysis"]]

    # Derived files can be regenerated; source database is opened read-only.
    export_frame = frame.copy()
    for column in ["distance_band", "bedroom_plot_group"]:
        export_frame[column] = export_frame[column].astype("string")
    temporary_database = args.processed / "analysis.tmp.sqlite"
    with sqlite3.connect(temporary_database) as database:
        export_frame.to_sql(
            "analysis_listings", database, index=False, if_exists="replace"
        )
        database.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS "
            "idx_analysis_id ON analysis_listings(id)"
        )
    temporary_database.replace(args.processed / "analysis.sqlite")
    dump(args.processed / "analysis_listings.json", records(export_frame))

    tables = {
        "rent_by_bedrooms": group_summary(rent_eligible, "bedroom_count"),
        "rent_by_bedroom_plot_group": group_summary(
            rent_eligible, "bedroom_plot_group"
        ),
        "rent_by_property_type": group_summary(rent_eligible, "propertyType"),
        "rent_by_distance": group_summary(rent_eligible, "distance_band"),
        "rent_by_zip": group_summary(rent_eligible, "zipCode"),
        "rent_per_sqft_by_bedrooms": group_summary(
            rent_eligible, "bedroom_count", "rent_per_sqft_usd"
        ),
        "one_bedroom_by_distance": group_summary(
            rent_eligible.loc[rent_eligible["bedroom_count"] == 1],
            "distance_band",
        ),
        "two_bedroom_by_distance": group_summary(
            rent_eligible.loc[rent_eligible["bedroom_count"] == 2],
            "distance_band",
        ),
    }
    for name, table in tables.items():
        dump(args.output / (name + ".json"), records(table))

    # Sensitivity result is separate; primary summaries retain all unique listings.
    medians_by_coordinate = rent_eligible.groupby(
        ["latitude", "longitude"], as_index=False
    )["monthly_rent_usd"].median()
    summary = {
        "snapshot_id": SNAPSHOT.name,
        "input_rows": len(source),
        "processed_rows": len(frame),
        "rent_analysis_n": len(rent_eligible),
        "area_analysis_n": len(area_eligible),
        "missing_area_n": int(frame["area_missing"].sum()),
        "invalid_nonmissing_area_n": int(frame["area_invalid_nonmissing"].sum()),
        "invalid_rent_n": int((~frame["rent_valid"]).sum()),
        "invalid_coordinates_n": int((~frame["coordinates_valid"]).sum()),
        "duplicate_ids_n": int(frame["id"].duplicated().sum()),
        "rent_iqr_review_n": int(frame["rent_iqr_review"].sum()),
        "multifamily_review_n": int(frame["multifamily_review"].sum()),
        "room_wording_review_n": int(frame["room_wording_review"].sum()),
        "area_extreme_review_n": int(frame["area_extreme_review"].sum()),
        "long_market_review_n": int(frame["long_market_review"].sum()),
        "shared_coordinate_records_n": int(
            frame["coordinate_cluster_size"].gt(1).sum()
        ),
        "distinct_coordinate_pairs": len(medians_by_coordinate),
        "largest_coordinate_cluster_n": int(
            frame["coordinate_cluster_size"].max()
        ),
        "monthly_rent_median_usd": float(rent_eligible["monthly_rent_usd"].median()),
        "monthly_rent_min_usd": float(rent_eligible["monthly_rent_usd"].min()),
        "monthly_rent_max_usd": float(rent_eligible["monthly_rent_usd"].max()),
        "rent_per_sqft_median_usd": float(
            area_eligible["rent_per_sqft_usd"].median()
        ),
        "coordinate_equal_weight_sensitivity_median_usd": float(
            medians_by_coordinate["monthly_rent_usd"].median()
        ),
        "coordinate_sensitivity_note": (
            "Median of per-coordinate medians; coordinates are a coarse cluster "
            "proxy, not verified buildings."
        ),
        "within_miles_counts": {
            str(radius): int(frame["distance_miles"].le(radius).sum())
            for radius in [1, 2, 3, 5, 10]
        },
        "distance_max_difference_from_frozen_miles": float(
            (frame["distance_miles"] - frame["distanceToCampusMiles"]).abs().max()
        ),
        "area_missing_policy": (
            "Retained for monthly-rent analysis; "
            "omitted only from rent-per-area analysis."
        ),
        "outlier_policy": (
            "Bedroom-specific 1.5 IQR flags for n>=4; "
            "no automated removal or winsorization."
        ),
        "observation_unit": (
            "One provider listing ID. Room-vs-entire-unit and "
            "floorplan-vs-specific-unit semantics are not independently verified."
        ),
    }

    plots(rent_eligible, args.output)
    source_hashes_after = hashes(SNAPSHOT)
    if source_hashes_before != source_hashes_after:
        raise RuntimeError("Frozen snapshot changed during analysis.")
    dump(args.output / "summary.json", summary)
    dump(
        args.output / "run_manifest.json",
        {
            "completed_at_utc": datetime.now(timezone.utc).isoformat(),
            "python": platform.python_version(),
            "packages": {
                name: importlib.metadata.version(name)
                for name in ["pandas", "numpy", "matplotlib"]
            },
            "source_sha256": source_hashes_before,
            "source_unchanged": True,
            "network_requests": 0,
            "entrypoint": "python scripts/run_member_a.py",
        },
    )
    print(json.dumps(summary, indent=2))
    print("Outputs:", args.output)


if __name__ == "__main__":
    main()
