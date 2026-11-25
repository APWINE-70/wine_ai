"""Reliability indices (SAIFI, SAIDI, CAIDI) and pre-aggregated dashboard metrics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


def compute_year_reliability(
    outages: pd.DataFrame,
    total_customers_served: int,
    year: int,
    cust_col: str = "customers_affected",
    dur_col: str = "duration_min",
    exclude_strict: bool = True,
    exclude_extreme: bool = False,
    exclude_storm_dates: tuple[str, ...] = (),
    exclude_storm_province: str | None = None,
) -> dict[str, Any]:
    """Compute SAIFI, SAIDI, CAIDI for a given year from unplanned outages only."""
    if total_customers_served <= 0:
        raise ValueError("total_customers_served must be positive.")

    df = outages[
        (outages["year"] == year)
        & (outages["outage_type"] == "Unplanned")
    ].copy()

    if exclude_strict and "is_excluded_from_strict" in df.columns:
        df = df[~df["is_excluded_from_strict"]]
    if exclude_extreme and "is_extreme_event" in df.columns:
        df = df[~df["is_extreme_event"]]
    if exclude_storm_dates and "start_date" in df.columns:
        date_str = pd.to_datetime(df["start_date"]).dt.strftime("%Y-%m-%d")
        storm_mask = date_str.isin(exclude_storm_dates)
        if exclude_storm_province is not None and "province" in df.columns:
            storm_mask = storm_mask & (df["province"] == exclude_storm_province)
        df = df[~storm_mask]

    valid_cust = df[cust_col].fillna(0).clip(lower=0)
    valid_dur = df[dur_col].fillna(0).clip(lower=0)
    customer_minutes = (valid_cust * valid_dur).sum()
    customers_sum = valid_cust.sum()

    saifi = float(customers_sum / total_customers_served)
    saidi = float(customer_minutes / total_customers_served)
    caidi = float(saidi / saifi) if saifi > 0 else 0.0

    return {
        "year": int(year),
        "outage_count": int(len(df)),
        "total_duration_min": round(float(valid_dur.sum()), 2),
        "total_customers_affected": int(round(float(customers_sum))),
        "total_customer_minutes": round(float(customer_minutes), 2),
        "total_customers_served": int(total_customers_served),
        "saifi": round(saifi, 4),
        "saidi": round(saidi, 4),
        "caidi": round(caidi, 4),
    }


def compute_dual_reliability_summary(
    outages: pd.DataFrame,
    feeders: pd.DataFrame,
) -> dict[str, Any]:
    """Compute inclusive, strict-clean, imputed, and without-storm reliability indices."""
    total_customers_imputed = int(feeders["customers_served"].dropna().sum())
    total_customers_raw = (
        int(feeders["customers_served_raw"].dropna().sum())
        if "customers_served_raw" in feeders.columns
        else total_customers_imputed
    )

    years = sorted(int(y) for y in outages["year"].dropna().unique() if y in (2023, 2024))
    if not years:
        years = [2023, 2024]

    planned_counts = {
        int(y): int(((outages["year"] == y) & (outages["outage_type"] == "Planned")).sum())
        for y in years
    }

    scenarios = {
        "raw_uncleaned_unplanned": {
            "total_customers": total_customers_raw,
            "cust_col": "customers_affected_raw" if "customers_affected_raw" in outages.columns else "customers_affected",
            "dur_col": "duration_min_raw" if "duration_min_raw" in outages.columns else "duration_min",
            "exclude_strict": False,
            "exclude_extreme": False,
            "exclude_storm_dates": (),
        },
        "clean_imputed_all_unplanned": {
            "total_customers": total_customers_imputed,
            "cust_col": "customers_affected_imputed" if "customers_affected_imputed" in outages.columns else "customers_affected",
            "dur_col": "duration_min_imputed" if "duration_min_imputed" in outages.columns else "duration_min",
            "exclude_strict": False,
            "exclude_extreme": False,
            "exclude_storm_dates": (),
        },
        "strict_clean": {
            "total_customers": total_customers_imputed,
            "cust_col": "customers_affected",
            "dur_col": "duration_min",
            "exclude_strict": True,
            "exclude_extreme": False,
            "exclude_storm_dates": (),
        },
        "clean_imputed_without_chiang_rai_storm": {
            "total_customers": total_customers_imputed,
            "cust_col": "customers_affected_imputed" if "customers_affected_imputed" in outages.columns else "customers_affected",
            "dur_col": "duration_min_imputed" if "duration_min_imputed" in outages.columns else "duration_min",
            "exclude_strict": False,
            "exclude_extreme": False,
            "exclude_storm_dates": ("2024-08-22", "2024-08-23"),
            "exclude_storm_province": "เชียงราย",
        },
        "strict_without_extremes": {
            "total_customers": total_customers_imputed,
            "cust_col": "customers_affected",
            "dur_col": "duration_min",
            "exclude_strict": True,
            "exclude_extreme": True,
            "exclude_storm_dates": (),
        },
    }

    results: dict[str, Any] = {
        "total_customers_served_imputed": total_customers_imputed,
        "total_customers_served_raw_non_null": total_customers_raw,
        "planned_outages_excluded_counts": planned_counts,
        "scenarios": {},
    }
    for name, cfg in scenarios.items():
        by_year = {
            str(y): compute_year_reliability(
                outages,
                cfg["total_customers"],
                y,
                cust_col=cfg["cust_col"],
                dur_col=cfg["dur_col"],
                exclude_strict=cfg["exclude_strict"],
                exclude_extreme=cfg["exclude_extreme"],
                exclude_storm_dates=cfg["exclude_storm_dates"],
                exclude_storm_province=cfg.get("exclude_storm_province"),
            )
            for y in years
        }
        if "2023" in by_year and "2024" in by_year:
            m23, m24 = by_year["2023"], by_year["2024"]
            by_year["yoy_change_2024_vs_2023"] = {
                "outage_count_delta": m24["outage_count"] - m23["outage_count"],
                "outage_count_pct": round(((m24["outage_count"] - m23["outage_count"]) / m23["outage_count"] * 100.0) if m23["outage_count"] else 0.0, 2),
                "saifi_delta": round(m24["saifi"] - m23["saifi"], 4),
                "saifi_pct": round(((m24["saifi"] - m23["saifi"]) / m23["saifi"] * 100.0) if m23["saifi"] else 0.0, 2),
                "saidi_delta": round(m24["saidi"] - m23["saidi"], 4),
                "saidi_pct": round(((m24["saidi"] - m23["saidi"]) / m23["saidi"] * 100.0) if m23["saidi"] else 0.0, 2),
                "caidi_delta": round(m24["caidi"] - m23["caidi"], 4),
            }
        results["scenarios"][name] = by_year
    return results


def build_dashboard_bundle(clean_dir: Path) -> dict[str, Any]:
    """Generate pre-aggregated JSON bundle for fast dashboard loading (Mission F)."""
    clean_dir = Path(clean_dir)
    outages = pd.read_parquet(clean_dir / "outages_enriched.parquet")
    feeders = pd.read_parquet(clean_dir / "feeders_clean.parquet")

    reliability = compute_dual_reliability_summary(outages, feeders)
    unplanned = outages[outages["outage_type"] == "Unplanned"].copy()
    cm_col = "customer_minutes_imputed" if "customer_minutes_imputed" in unplanned.columns else "customer_minutes"
    dur_col = "duration_min_imputed" if "duration_min_imputed" in unplanned.columns else "duration_min"

    by_cause = (
        unplanned.groupby("cause", dropna=False)
        .agg(
            outage_count=("outage_id", "count"),
            total_duration_min=(dur_col, "sum"),
            total_customer_minutes=(cm_col, "sum"),
        )
        .reset_index()
        .sort_values("total_customer_minutes", ascending=False)
        .to_dict(orient="records")
    )

    by_feeder = (
        unplanned[~unplanned["is_orphan_feeder"]]
        .groupby(["feeder_id", "province", "area_type"], dropna=False)
        .agg(
            outage_count=("outage_id", "count"),
            total_duration_min=(dur_col, "sum"),
            total_customer_minutes=(cm_col, "sum"),
        )
        .reset_index()
        .sort_values("total_customer_minutes", ascending=False)
        .to_dict(orient="records")
    )

    bundle = {
        "data_cutoff": "2024-12-31 23:59",
        "reliability": reliability,
        "by_cause": by_cause,
        "by_feeder": by_feeder,
    }
    (clean_dir / "dashboard_bundle.json").write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return bundle


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute SAIFI/SAIDI/CAIDI and dashboard aggregates.")
    parser.add_argument("--clean-dir", type=Path, default=Path("data/clean"))
    args = parser.parse_args()

    bundle = build_dashboard_bundle(args.clean_dir)
    print(json.dumps(bundle["reliability"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
