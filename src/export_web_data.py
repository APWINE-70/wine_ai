"""Build compact web dashboard JSON data bundle from Phase 1-2 clean datasets."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def build_web_data(
    clean_dir: Path = Path("data/clean"),
    analytics_path: Path = Path("docs/web_analytics.json"),
    out_path: Path = Path("web/src/data/dashboard_data.json"),
) -> None:
    outages = pd.read_parquet(clean_dir / "outages_enriched.parquet")
    feeders = pd.read_parquet(clean_dir / "feeders_clean.parquet")
    substations = pd.read_parquet(clean_dir / "substations_clean.parquet")
    analytics = json.loads(analytics_path.read_text(encoding="utf-8"))

    sub_prov = substations.set_index("substation_id")["province"].to_dict()
    feeders_out = feeders.copy()
    feeders_out["province"] = feeders_out["substation_id"].map(sub_prov)

    unplanned = outages[outages["outage_type"] == "Unplanned"].copy()
    date_str = pd.to_datetime(unplanned["start_date"]).dt.strftime("%Y-%m-%d")
    is_cri_storm = (unplanned["province"] == "เชียงราย") & date_str.isin(["2024-08-22", "2024-08-23"])

    events = []
    for row, d_str, storm_flag in zip(unplanned.itertuples(index=False), date_str.tolist(), is_cri_storm.tolist()):
        events.append({
            "id": str(row.outage_id),
            "f": str(row.feeder_id),
            "y": int(row.year),
            "m": int(row.month),
            "d": int(pd.Timestamp(row.start_time).day_of_week),
            "h": int(row.hour),
            "dt": d_str,
            "p": None if pd.isna(row.province) else str(row.province),
            "a": None if pd.isna(row.area_type) else str(row.area_type),
            "c": str(row.cause),
            "dur": round(float(row.duration_min_imputed), 1),
            "cust": int(row.customers_affected_imputed),
            "cm": round(float(row.customer_minutes_imputed), 1),
            "crew": None if pd.isna(row.crew_arrival_min) else round(float(row.crew_arrival_min), 1),
            "storm": bool(storm_flag),
            "ext": bool(row.is_extreme_event),
            "orp": bool(row.is_orphan_feeder),
        })

    feeder_records = [
        {
            "feeder_id": str(r.feeder_id),
            "substation_id": str(r.substation_id),
            "province": str(r.province),
            "area_type": str(r.area_type),
            "length_km": round(float(r.length_km), 2),
            "customers_served": int(r.customers_served),
            "tree_cover": str(r.tree_cover),
            "overhead_pct": float(r.overhead_pct),
            "install_year": int(r.install_year),
        }
        for r in feeders_out.itertuples(index=False)
    ]

    payload = {
        "metadata": analytics["metadata"],
        "reliability": analytics["q1_reliability_overview"],
        "storm_reconciliation": analytics["storm_reconciliation_2024_08_22_23"],
        "weather_analysis": analytics["q5_weather_analysis"],
        "restoration_analysis": analytics["q6_restoration_analysis"],
        "three_projects": analytics["q7_three_project_simulation"],
        "aging_alerts": analytics["q3_feeder_priority"]["aging_equipment_alerts"],
        "tree_cover_normalized": analytics["q3_feeder_priority"]["tree_cover_normalized"],
        "feeders": feeder_records,
        "events": events,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {out_path} ({out_path.stat().st_size / 1024:.1f} KB, {len(events)} events)")


if __name__ == "__main__":
    build_web_data()
