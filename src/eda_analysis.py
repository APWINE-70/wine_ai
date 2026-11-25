"""Phase 2 (Mission B): Statistical EDA, 7 Executive Answers, and docs/web_analytics.json generator."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.metrics import compute_dual_reliability_summary

DAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
RAINY_MONTHS = {5, 6, 7, 8, 9, 10}


def _summary_stats(series: pd.Series) -> dict[str, float | int | None]:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty:
        return {"count": 0, "mean": None, "median": None, "iqr": None, "p90": None, "p95": None, "min": None, "max": None}
    q1, q3 = clean.quantile([0.25, 0.75])
    return {
        "count": int(len(clean)),
        "mean": round(float(clean.mean()), 2),
        "median": round(float(clean.median()), 2),
        "iqr": round(float(q3 - q1), 2),
        "p90": round(float(clean.quantile(0.90)), 2),
        "p95": round(float(clean.quantile(0.95)), 2),
        "min": round(float(clean.min()), 2),
        "max": round(float(clean.max()), 2),
    }


def _compute_storm_reconciliation(unplanned: pd.DataFrame, total_customers_served: int) -> dict[str, Any]:
    date_str = pd.to_datetime(unplanned["start_date"]).dt.strftime("%Y-%m-%d")
    storm_mask = (unplanned["province"] == "เชียงราย") & date_str.isin(["2024-08-22", "2024-08-23"])
    storm_df = unplanned.loc[storm_mask]

    y2024 = unplanned[unplanned["year"] == 2024]
    y2024_cm = float(y2024["customer_minutes_imputed"].sum())
    storm_cm = float(storm_df["customer_minutes_imputed"].sum())
    storm_cust = int(storm_df["customers_affected_imputed"].sum())

    return {
        "storm_dates": ["2024-08-22", "2024-08-23"],
        "province": "เชียงราย",
        "storm_event_count": int(len(storm_df)),
        "storm_duration_min_sum": round(float(storm_df["duration_min_imputed"].sum()), 2),
        "storm_customers_affected_sum": storm_cust,
        "storm_customer_minutes": round(storm_cm, 2),
        "share_of_2024_events_pct": round(len(storm_df) / len(y2024) * 100.0, 2) if len(y2024) else 0.0,
        "share_of_2024_customer_minutes_pct": round(storm_cm / y2024_cm * 100.0, 2) if y2024_cm else 0.0,
        "saidi_contribution_2024_min": round(storm_cm / total_customers_served, 4),
        "saifi_contribution_2024": round(storm_cust / total_customers_served, 4),
    }


def _compute_feeder_rankings(
    unplanned: pd.DataFrame,
    feeders: pd.DataFrame,
    substations: pd.DataFrame,
) -> dict[str, Any]:
    valid = unplanned[~unplanned["is_orphan_feeder"]].copy()
    total_cm = float(valid["customer_minutes_imputed"].sum())

    # Map province onto feeders
    sub_prov = substations.set_index("substation_id")["province"].to_dict()
    f_meta = feeders.copy()
    f_meta["province"] = f_meta["substation_id"].map(sub_prov)

    agg = (
        valid.groupby("feeder_id")
        .agg(
            outage_count=("outage_id", "count"),
            outage_count_2023=("year", lambda s: int((s == 2023).sum())),
            outage_count_2024=("year", lambda s: int((s == 2024).sum())),
            median_duration_min=("duration_min_imputed", "median"),
            total_duration_min=("duration_min_imputed", "sum"),
            total_customers_affected=("customers_affected_imputed", "sum"),
            total_customer_minutes=("customer_minutes_imputed", "sum"),
            top_cause=("cause", lambda s: s.value_counts().index[0]),
            equip_2023=("cause", lambda s: int(((s == "equipment") & (valid.loc[s.index, "year"] == 2023)).sum())),
            equip_2024=("cause", lambda s: int(((s == "equipment") & (valid.loc[s.index, "year"] == 2024)).sum())),
        )
        .reset_index()
    )

    merged = f_meta.merge(agg, on="feeder_id", how="left").fillna({"outage_count": 0, "total_customer_minutes": 0.0})
    merged["cm_share_pct"] = (merged["total_customer_minutes"] / total_cm * 100.0).round(2) if total_cm else 0.0
    merged["events_per_100km_per_year"] = (merged["outage_count"] / (merged["length_km"] * 2.0) * 100.0).round(2)
    merged["saidi_contribution_2yr_min"] = (merged["total_customer_minutes"] / feeders["customers_served"].sum()).round(2)

    ranked = merged.sort_values("total_customer_minutes", ascending=False).reset_index(drop=True)
    top5 = ranked.head(5)

    # Tree cover normalized by length (events from tree per 100 km per year)
    tree_events = valid[valid["cause"] == "tree"].groupby("feeder_id")["outage_id"].count().rename("tree_events")
    f_tree = f_meta.merge(tree_events, on="feeder_id", how="left").fillna({"tree_events": 0})
    tree_cover_stats = (
        f_tree.groupby("tree_cover")
        .agg(
            feeder_count=("feeder_id", "count"),
            total_length_km=("length_km", "sum"),
            tree_events=("tree_events", "sum"),
        )
        .reset_index()
    )
    tree_cover_stats["tree_events_per_100km_per_year"] = (
        tree_cover_stats["tree_events"] / (tree_cover_stats["total_length_km"] * 2.0) * 100.0
    ).round(2)

    # Aging equipment surge detection (2023 vs 2024 equipment failures)
    merged["equip_delta"] = merged["equip_2024"] - merged["equip_2023"]
    aging_alerts = (
        merged[merged["equip_2024"] >= 10]
        .sort_values(["equip_delta", "equip_2024"], ascending=False)
        [["feeder_id", "province", "area_type", "install_year", "equip_2023", "equip_2024", "equip_delta", "total_customer_minutes"]]
        .to_dict(orient="records")
    )

    cols_keep = [
        "feeder_id", "province", "area_type", "length_km", "customers_served",
        "tree_cover", "overhead_pct", "install_year", "outage_count",
        "outage_count_2023", "outage_count_2024", "median_duration_min",
        "total_customer_minutes", "cm_share_pct", "events_per_100km_per_year", "top_cause",
    ]
    return {
        "top5_feeders": top5[cols_keep].round(2).to_dict(orient="records"),
        "top5_cumulative_cm_share_pct": round(float(top5["cm_share_pct"].sum()), 2),
        "all_feeders_ranked": ranked[cols_keep].round(2).to_dict(orient="records"),
        "tree_cover_normalized": tree_cover_stats.round(2).to_dict(orient="records"),
        "aging_equipment_alerts": aging_alerts,
    }


def _compute_temporal_patterns(unplanned: pd.DataFrame) -> dict[str, Any]:
    df = unplanned.copy()
    df["dow"] = df["start_time"].dt.day_of_week
    df["is_rainy_season"] = df["month"].isin(RAINY_MONTHS)

    monthly = (
        df.groupby(["year", "month"])
        .agg(
            outage_count=("outage_id", "count"),
            total_customer_minutes=("customer_minutes_imputed", "sum"),
            tree_count=("cause", lambda s: int((s == "tree").sum())),
            lightning_count=("cause", lambda s: int((s == "lightning").sum())),
            animal_count=("cause", lambda s: int((s == "animal").sum())),
            equipment_count=("cause", lambda s: int((s == "equipment").sum())),
        )
        .reset_index()
        .sort_values(["year", "month"])
    )

    monthly_overall = (
        df.groupby("month")
        .agg(
            outage_count=("outage_id", "count"),
            total_customer_minutes=("customer_minutes_imputed", "sum"),
        )
        .reset_index()
        .sort_values("month")
    )

    hourly = (
        df.groupby("hour")
        .agg(
            outage_count=("outage_id", "count"),
            total_customer_minutes=("customer_minutes_imputed", "sum"),
        )
        .reset_index()
        .sort_values("hour")
    )

    # 24x7 heatmap (day_of_week 0..6 x hour 0..23)
    heatmap_grid = (
        df.groupby(["dow", "hour"])
        .agg(outage_count=("outage_id", "count"), total_customer_minutes=("customer_minutes_imputed", "sum"))
        .reset_index()
    )
    heatmap_grid["day_name"] = heatmap_grid["dow"].map(lambda d: DAY_NAMES[int(d)])

    # Cause by time-of-day window & rainy season shares
    cause_time_profile: list[dict[str, Any]] = []
    for cause, grp in df.groupby("cause"):
        n = len(grp)
        rainy_pct = float(grp["is_rainy_season"].mean() * 100.0)
        morning_pct = float(grp["hour"].between(5, 9).mean() * 100.0)
        afternoon_pct = float(grp["hour"].between(14, 18).mean() * 100.0)
        evening_pct = float(grp["hour"].between(18, 22).mean() * 100.0)
        peak_hour = int(grp["hour"].value_counts().index[0])
        cause_time_profile.append({
            "cause": cause,
            "count": int(n),
            "rainy_season_may_oct_pct": round(rainy_pct, 1),
            "morning_05_09_pct": round(morning_pct, 1),
            "afternoon_14_18_pct": round(afternoon_pct, 1),
            "evening_18_22_pct": round(evening_pct, 1),
            "peak_hour": peak_hour,
        })

    return {
        "rainy_season_may_oct_share_pct": round(float(df["is_rainy_season"].mean() * 100.0), 2),
        "peak_month_overall": int(monthly_overall.sort_values("outage_count", ascending=False).iloc[0]["month"]),
        "monthly_by_year": monthly.round(2).to_dict(orient="records"),
        "monthly_overall": monthly_overall.round(2).to_dict(orient="records"),
        "hourly_overall": hourly.round(2).to_dict(orient="records"),
        "heatmap_24x7": heatmap_grid.round(2).to_dict(orient="records"),
        "cause_time_profile": sorted(cause_time_profile, key=lambda r: r["count"], reverse=True),
    }


def _compute_weather_analysis(unplanned: pd.DataFrame, weather: pd.DataFrame) -> dict[str, Any]:
    # Aggregate unplanned outages per (province, date) using valid non-orphan records (which have province)
    valid_prov = unplanned[unplanned["province"].notna()].copy()
    daily_out = (
        valid_prov.groupby(["start_date", "province"])
        .agg(
            outage_count=("outage_id", "count"),
            customer_minutes=("customer_minutes_imputed", "sum"),
        )
        .reset_index()
        .rename(columns={"start_date": "date"})
    )

    wx = weather.merge(daily_out, on=["date", "province"], how="left")
    wx["outage_count"] = wx["outage_count"].fillna(0)
    wx["customer_minutes"] = wx["customer_minutes"].fillna(0.0)

    storm_days = wx[wx["thunderstorm"] == True]  # noqa: E712
    normal_days = wx[wx["thunderstorm"] == False]  # noqa: E712

    rain_bins = pd.cut(
        wx["rainfall_mm"],
        bins=[-0.01, 0.0, 10.0, 35.0, 1000.0],
        labels=["No Rain (0 mm)", "Light (0-10 mm)", "Moderate (10-35 mm)", "Heavy (>35 mm)"],
    )
    by_rain_tier = (
        wx.assign(rain_tier=rain_bins)
        .groupby("rain_tier", observed=False)
        .agg(
            province_days=("date", "count"),
            avg_outages_per_day=("outage_count", "mean"),
            total_outages=("outage_count", "sum"),
        )
        .reset_index()
    )

    wind_bins = pd.cut(
        wx["max_wind_kmh"],
        bins=[-0.01, 25.0, 45.0, 1000.0],
        labels=["Calm (<=25 km/h)", "Moderate (25-45 km/h)", "High Wind (>45 km/h)"],
    )
    by_wind_tier = (
        wx.assign(wind_tier=wind_bins)
        .groupby("wind_tier", observed=False)
        .agg(
            province_days=("date", "count"),
            avg_outages_per_day=("outage_count", "mean"),
            total_outages=("outage_count", "sum"),
        )
        .reset_index()
    )

    # Compute Pearson and Spearman correlations safely
    corr_rain_pearson = float(wx[["rainfall_mm", "outage_count"]].dropna().corr(method="pearson").iloc[0, 1])
    corr_rain_spearman = float(wx[["rainfall_mm", "outage_count"]].dropna().corr(method="spearman").iloc[0, 1])
    corr_wind_pearson = float(wx[["max_wind_kmh", "outage_count"]].dropna().corr(method="pearson").iloc[0, 1])
    corr_wind_spearman = float(wx[["max_wind_kmh", "outage_count"]].dropna().corr(method="spearman").iloc[0, 1])
    corr_temp_pearson = float(wx[["max_temp_c", "outage_count"]].dropna().corr(method="pearson").iloc[0, 1])

    return {
        "observed_province_days": int(len(wx)),
        "missing_province_days_not_joined": 2924 - int(len(wx)),
        "thunderstorm_comparison": {
            "thunderstorm_days_count": int(len(storm_days)),
            "thunderstorm_avg_outages_per_province_day": round(float(storm_days["outage_count"].mean()), 3),
            "non_thunderstorm_days_count": int(len(normal_days)),
            "non_thunderstorm_avg_outages_per_province_day": round(float(normal_days["outage_count"].mean()), 3),
            "thunderstorm_risk_multiplier": round(
                float(storm_days["outage_count"].mean() / normal_days["outage_count"].mean()), 2
            ),
        },
        "correlations_daily_province": {
            "rainfall_mm_pearson": round(corr_rain_pearson, 4),
            "rainfall_mm_spearman": round(corr_rain_spearman, 4),
            "max_wind_kmh_pearson": round(corr_wind_pearson, 4),
            "max_wind_kmh_spearman": round(corr_wind_spearman, 4),
            "max_temp_c_pearson": round(corr_temp_pearson, 4),
        },
        "by_rain_tier": by_rain_tier.round(3).to_dict(orient="records"),
        "by_wind_tier": by_wind_tier.round(3).to_dict(orient="records"),
    }


def _compute_restoration_analysis(unplanned: pd.DataFrame) -> dict[str, Any]:
    valid = unplanned[unplanned["area_type"].notna()].copy()

    by_area: list[dict[str, Any]] = []
    for area in ("Urban", "Suburban", "Rural"):
        grp = valid[valid["area_type"] == area]
        crew_valid = grp[grp["crew_arrival_min"].notna()]
        share_ratio = (crew_valid["crew_arrival_min"] / crew_valid["duration_min_imputed"]).clip(upper=1.0)
        by_area.append({
            "area_type": area,
            "outage_count": int(len(grp)),
            "duration_median_min": round(float(grp["duration_min_imputed"].median()), 1),
            "duration_mean_min": round(float(grp["duration_min_imputed"].mean()), 1),
            "duration_p95_min": round(float(grp["duration_min_imputed"].quantile(0.95)), 1),
            "crew_arrival_median_min": round(float(crew_valid["crew_arrival_min"].median()), 1),
            "crew_arrival_mean_min": round(float(crew_valid["crew_arrival_min"].mean()), 1),
            "median_crew_share_of_duration_pct": round(float(share_ratio.median() * 100.0), 1),
            "mean_crew_share_of_duration_pct": round(float(share_ratio.mean() * 100.0), 1),
            "caidi_min": round(float(grp["customer_minutes_imputed"].sum() / grp["customers_affected_imputed"].sum()), 1),
        })

    crew_df = valid[["crew_arrival_min", "duration_min_imputed"]].dropna()
    corr_pearson = float(crew_df.corr(method="pearson").iloc[0, 1])
    corr_spearman = float(crew_df.corr(method="spearman").iloc[0, 1])

    # OLS slope: duration_min ~ a + b * crew_arrival_min
    slope, intercept = np.polyfit(crew_df["crew_arrival_min"], crew_df["duration_min_imputed"], 1)

    return {
        "by_area_type": by_area,
        "crew_vs_duration_pearson": round(corr_pearson, 4),
        "crew_vs_duration_spearman": round(corr_spearman, 4),
        "crew_to_duration_ols_slope": round(float(slope), 3),
        "crew_to_duration_ols_intercept": round(float(intercept), 2),
        "crew_non_null_count": int(len(crew_df)),
    }


def _compute_three_project_simulation(
    unplanned: pd.DataFrame,
    total_customers_served: int,
) -> dict[str, Any]:
    """Simulate 3 evidence-based projects on 2024 baseline SAIDI."""
    y24 = unplanned[unplanned["year"] == 2024].copy()
    baseline_cm_2024 = float(y24["customer_minutes_imputed"].sum())
    baseline_saidi_2024 = baseline_cm_2024 / total_customers_served

    # Project 1: Intensive vegetation management & covered conductor on Top 5 high-damage Rural feeders
    top5_ids = ("CRI-F11", "CRI-F03", "CRI-F04", "LPG-F09", "CRI-F13")
    p1_pool = y24[y24["feeder_id"].isin(top5_ids) & (y24["cause"] == "tree")]
    p1_reduction_rate = 0.65  # Conservative 65% reduction in tree-contact customer-minutes on treated feeders
    p1_saved_cm = float(p1_pool["customer_minutes_imputed"].sum()) * p1_reduction_rate
    p1_saved_saidi = p1_saved_cm / total_customers_served

    # Project 2: Rural Chiang Rai crew forward-staging + storm response protocol (reduces crew travel ~20 min in Rural CRI)
    p2_pool = y24[(y24["province"] == "เชียงราย") & (y24["area_type"] == "Rural") & (~y24["feeder_id"].isin(top5_ids) | (y24["cause"] != "tree"))]
    # Also include non-tree outages on all Rural CRI feeders + remaining duration saving of 20 min per event
    p2_rural_cri = y24[(y24["province"] == "เชียงราย") & (y24["area_type"] == "Rural")]
    avg_min_saved_per_event = 20.0
    p2_saved_cm = float((p2_rural_cri["customers_affected_imputed"] * avg_min_saved_per_event).sum())
    # Avoid double-counting 65% of tree events on top-4 CRI feeders already removed in Project 1
    overlap_cm = float(
        (y24[y24["feeder_id"].isin(("CRI-F11", "CRI-F03", "CRI-F04", "CRI-F13")) & (y24["cause"] == "tree")]["customers_affected_imputed"] * avg_min_saved_per_event).sum()
    ) * p1_reduction_rate
    p2_saved_cm_net = max(0.0, p2_saved_cm - overlap_cm)
    p2_saved_saidi = p2_saved_cm_net / total_customers_served

    # Project 3: Aging equipment replacement (CMI-F14 + top equipment-failure feeders) & animal guards on morning-peak feeders
    equip_target_feeders = ("CMI-F14", "CRI-F11", "CRI-F03", "CMI-F10", "CRI-F10")
    p3_equip_pool = y24[y24["feeder_id"].isin(equip_target_feeders) & (y24["cause"] == "equipment")]
    p3_animal_pool = y24[y24["cause"] == "animal"]
    p3_saved_cm = float(p3_equip_pool["customer_minutes_imputed"].sum()) * 0.70 + float(p3_animal_pool["customer_minutes_imputed"].sum()) * 0.50
    p3_saved_saidi = p3_saved_cm / total_customers_served

    total_saved_saidi = p1_saved_saidi + p2_saved_saidi + p3_saved_saidi
    projected_saidi_2024 = baseline_saidi_2024 - total_saved_saidi

    projects = [
        {
            "project_id": "P1",
            "title": "ตัดแต่งกิ่งไม้เชิงรุกก่อนฤดูฝน + เปลี่ยนสายหุ้มฉนวน (Tree Cover High)",
            "target_scope": "สายป้อน Top 5: CRI-F11, CRI-F03, CRI-F04, LPG-F09, CRI-F13 (เฉพาะเหตุจากต้นไม้)",
            "baseline_target_cm_2024": round(float(p1_pool["customer_minutes_imputed"].sum()), 1),
            "assumption": "ลดผลกระทบเหตุจากต้นไม้ในสายป้อนเป้าหมายลง 65%",
            "estimated_saidi_reduction_min": round(p1_saved_saidi, 2),
            "share_of_total_reduction_pct": round(p1_saved_saidi / total_saved_saidi * 100.0, 1) if total_saved_saidi else 0.0,
        },
        {
            "project_id": "P2",
            "title": "ตั้งจุดเตรียมทีมช่างส่วนหน้าในชนบทเชียงราย + แผนรับมือพายุ",
            "target_scope": "สายป้อนเขตชนบท จังหวัดเชียงราย (ลดเวลาเดินทาง/กู้คืนเฉลี่ย 20 นาที/ครั้ง)",
            "baseline_target_cm_2024": round(float(p2_rural_cri["customer_minutes_imputed"].sum()), 1),
            "assumption": "ลดเวลาเดินทางและกู้คืนลงเฉลี่ย 20 นาทีต่อเหตุการณ์ในชนบทเชียงราย (หักซ้ำซ้อน P1 แล้ว)",
            "estimated_saidi_reduction_min": round(p2_saved_saidi, 2),
            "share_of_total_reduction_pct": round(p2_saved_saidi / total_saved_saidi * 100.0, 1) if total_saved_saidi else 0.0,
        },
        {
            "project_id": "P3",
            "title": "เปลี่ยนอุปกรณ์เสื่อมสภาพเร่งด่วน (CMI-F14 และสายเสี่ยง) + ติดตั้งอุปกรณ์ป้องกันสัตว์",
            "target_scope": "เปลี่ยนอุปกรณ์บน CMI-F14 และสายป้อนหลัก (ลดเหตุอุปกรณ์ 70%) + กันสัตว์ช่วงเช้า (ลดเหตุสัตว์ 50%)",
            "baseline_target_cm_2024": round(float(p3_equip_pool["customer_minutes_imputed"].sum() + p3_animal_pool["customer_minutes_imputed"].sum()), 1),
            "assumption": "ลดเหตุอุปกรณ์ชำรุดในสายเป้าหมาย 70% และเหตุจากสัตว์ทั้งระบบ 50%",
            "estimated_saidi_reduction_min": round(p3_saved_saidi, 2),
            "share_of_total_reduction_pct": round(p3_saved_saidi / total_saved_saidi * 100.0, 1) if total_saved_saidi else 0.0,
        },
    ]

    return {
        "baseline_2024_saidi_min": round(baseline_saidi_2024, 2),
        "estimated_total_saidi_reduction_min": round(total_saved_saidi, 2),
        "estimated_total_saidi_reduction_pct": round(total_saved_saidi / baseline_saidi_2024 * 100.0, 2) if baseline_saidi_2024 else 0.0,
        "projected_2024_saidi_min": round(projected_saidi_2024, 2),
        "projects": projects,
    }


def run_eda_analysis(clean_dir: Path, out_json: Path) -> dict[str, Any]:
    """Compute complete Phase 2 analytics bundle from cleaned parquet files."""
    clean_dir = Path(clean_dir)
    outages = pd.read_parquet(clean_dir / "outages_enriched.parquet")
    feeders = pd.read_parquet(clean_dir / "feeders_clean.parquet")
    substations = pd.read_parquet(clean_dir / "substations_clean.parquet")
    weather = pd.read_parquet(clean_dir / "weather_clean.parquet")

    total_customers_served = int(feeders["customers_served"].dropna().sum())
    unplanned = outages[outages["outage_type"] == "Unplanned"].copy()
    reliability = compute_dual_reliability_summary(outages, feeders)
    storm_recon = _compute_storm_reconciliation(unplanned, total_customers_served)

    # Cause summary (frequency vs customer-minutes)
    total_unplanned_events = len(unplanned)
    total_unplanned_cm = float(unplanned["customer_minutes_imputed"].sum())
    cause_summary = (
        unplanned.groupby("cause")
        .agg(
            outage_count=("outage_id", "count"),
            duration_median_min=("duration_min_imputed", "median"),
            duration_mean_min=("duration_min_imputed", "mean"),
            total_duration_min=("duration_min_imputed", "sum"),
            total_customers_affected=("customers_affected_imputed", "sum"),
            total_customer_minutes=("customer_minutes_imputed", "sum"),
        )
        .reset_index()
        .sort_values("total_customer_minutes", ascending=False)
    )
    cause_summary["event_share_pct"] = (cause_summary["outage_count"] / total_unplanned_events * 100.0).round(2)
    cause_summary["cm_share_pct"] = (cause_summary["total_customer_minutes"] / total_unplanned_cm * 100.0).round(2)

    # Province summary
    province_summary = (
        unplanned[~unplanned["is_orphan_feeder"]]
        .groupby("province")
        .agg(
            outage_count=("outage_id", "count"),
            total_customer_minutes=("customer_minutes_imputed", "sum"),
            duration_median_min=("duration_min_imputed", "median"),
        )
        .reset_index()
        .sort_values("total_customer_minutes", ascending=False)
    )

    analytics = {
        "metadata": {
            "data_cutoff": "2024-12-31 23:59",
            "feeder_export_date": "2025-01-05",
            "total_clean_events": int(len(outages)),
            "unplanned_events": int(len(unplanned)),
            "planned_events": int((outages["outage_type"] == "Planned").sum()),
            "orphan_feeder_events": int(outages["is_orphan_feeder"].sum()),
            "total_customers_served_imputed": total_customers_served,
            "total_customers_served_raw_non_null": int(feeders["customers_served_raw"].dropna().sum()),
        },
        "distribution_stats_unplanned": {
            "duration_min_imputed": _summary_stats(unplanned["duration_min_imputed"]),
            "duration_min_strict": _summary_stats(unplanned.loc[~unplanned["is_excluded_from_strict"], "duration_min"]),
            "customers_affected_imputed": _summary_stats(unplanned["customers_affected_imputed"]),
            "customers_affected_strict": _summary_stats(unplanned.loc[~unplanned["is_excluded_from_strict"], "customers_affected"]),
            "crew_arrival_min": _summary_stats(unplanned["crew_arrival_min"]),
            "extreme_event_count": int(unplanned["is_extreme_event"].sum()),
        },
        "q1_reliability_overview": reliability,
        "storm_reconciliation_2024_08_22_23": storm_recon,
        "q2_cause_impact": cause_summary.round(2).to_dict(orient="records"),
        "q3_feeder_priority": _compute_feeder_rankings(unplanned, feeders, substations),
        "q4_temporal_patterns": _compute_temporal_patterns(unplanned),
        "q5_weather_analysis": _compute_weather_analysis(unplanned, weather),
        "q6_restoration_analysis": _compute_restoration_analysis(unplanned),
        "q7_three_project_simulation": _compute_three_project_simulation(unplanned, total_customers_served),
        "by_province": province_summary.round(2).to_dict(orient="records"),
    }

    out_json = Path(out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(analytics, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return analytics


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase 2 EDA and build docs/web_analytics.json.")
    parser.add_argument("--clean-dir", type=Path, default=Path("data/clean"))
    parser.add_argument("--out-json", type=Path, default=Path("docs/web_analytics.json"))
    args = parser.parse_args()

    analytics = run_eda_analysis(args.clean_dir, args.out_json)
    print(f"Saved Phase 2 analytics to {args.out_json}")
    print("Storm recon:", json.dumps(analytics["storm_reconciliation_2024_08_22_23"], ensure_ascii=False))
    print("Q7 simulation:", json.dumps(analytics["q7_three_project_simulation"], ensure_ascii=False))


if __name__ == "__main__":
    main()
