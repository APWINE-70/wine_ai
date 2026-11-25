"""Mission A: Reproducible data cleaning and enrichment pipeline with zero silent drops."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.schema import (
    AREA_TYPE_ALIASES,
    CAUSE_ALIASES,
    DATE_WINDOW_END,
    DATE_WINDOW_START,
    OUTAGE_TYPE_ALIASES,
    PROVINCE_ALIASES,
    canonicalize_title,
    canonicalize_with_map,
    clean_str_series,
    load_raw_tables,
    normalize_feeder_id,
    normalize_year_value,
    parse_boolean_series,
    parse_comma_numeric,
    parse_flexible_datetime,
    parse_numeric_with_unit,
    parse_percentage,
    standardize_columns,
)

_OUTAGE_YEAR_RE = re.compile(r"OUT-(\d{4})-")


def _clean_substations(raw_sub: pd.DataFrame, audit_events: list[dict[str, Any]]) -> pd.DataFrame:
    df = standardize_columns(raw_sub)
    raw_count = len(df)

    df["substation_id"] = clean_str_series(df["substation_id"]).str.upper()
    df["substation_name"] = canonicalize_title(df["substation_name"])
    raw_cap_str = clean_str_series(df["capacity_mva"])
    df["capacity_mva"] = parse_numeric_with_unit(df["capacity_mva"])
    unit_stripped = int((raw_cap_str.notna() & pd.to_numeric(raw_cap_str, errors="coerce").isna() & df["capacity_mva"].notna()).sum())
    df["commissioned_year"], comm_be = normalize_year_value(df["commissioned_year"])
    df["province"] = canonicalize_with_map(df["province"], PROVINCE_ALIASES)
    df["region"] = canonicalize_title(df["region"])

    dup_mask = df["substation_id"].duplicated(keep="first") & df["substation_id"].notna()
    dup_count = int(dup_mask.sum())
    if dup_count > 0:
        df = df.loc[~dup_mask].copy()
        audit_events.append({
            "table": "substations",
            "action": "drop_duplicate_pk",
            "count": dup_count,
            "reason": "Duplicate substation_id kept first deterministic occurrence.",
        })

    audit_events.append({
        "table": "substations",
        "action": "strip_unit_from_capacity_mva",
        "count": unit_stripped,
        "reason": "Extracted numeric capacity_mva from unit strings such as '75 MVA'.",
    })
    if comm_be.sum() > 0:
        audit_events.append({
            "table": "substations",
            "action": "normalize_buddhist_era_year",
            "count": int(comm_be.sum()),
            "reason": "Converted commissioned_year >= 2400 from BE to CE.",
        })
    assert len(df) + dup_count == raw_count
    return df.sort_values("substation_id").reset_index(drop=True)


def _clean_feeders(
    raw_feeders: pd.DataFrame,
    valid_substation_ids: set[str],
    audit_events: list[dict[str, Any]],
) -> pd.DataFrame:
    df = standardize_columns(raw_feeders)
    raw_count = len(df)

    df["feeder_id"] = normalize_feeder_id(df["feeder_id"])
    df["substation_id"] = clean_str_series(df["substation_id"]).str.upper()
    df["area_type"] = canonicalize_with_map(df["area_type"], AREA_TYPE_ALIASES)

    df["length_km_raw"] = pd.to_numeric(clean_str_series(df["length_km"]), errors="coerce")
    len_metres_mask = df["length_km_raw"].notna() & (df["length_km_raw"] > 1000)
    df["length_km"] = df["length_km_raw"].where(~len_metres_mask, df["length_km_raw"] / 1000.0)
    df["is_length_converted_from_metres"] = len_metres_mask

    df["customers_served_raw"] = parse_comma_numeric(df["customers_served"]).round().astype("Int64")
    # Impute missing feeder customer totals deterministically using same area_type median
    area_medians = df.groupby("area_type")["customers_served_raw"].median().to_dict()
    global_median = float(df["customers_served_raw"].median()) if df["customers_served_raw"].notna().any() else 0.0
    imputed_cust = df["area_type"].map(area_medians).fillna(global_median).round().astype("Int64")
    miss_cust_mask = df["customers_served_raw"].isna()
    df["customers_served"] = df["customers_served_raw"].where(~miss_cust_mask, imputed_cust)
    df["is_customers_served_imputed"] = miss_cust_mask

    df["tree_cover"] = clean_str_series(df["tree_cover"]).str.lower()
    df["overhead_pct"] = parse_percentage(df["overhead_pct"])
    df["install_year"], inst_be = normalize_year_value(df["install_year"])
    df["is_orphan_substation"] = df["substation_id"].notna() & ~df["substation_id"].isin(valid_substation_ids)

    dup_mask = df["feeder_id"].duplicated(keep="first") & df["feeder_id"].notna()
    dup_count = int(dup_mask.sum())
    if dup_count > 0:
        df = df.loc[~dup_mask].copy()
        audit_events.append({
            "table": "feeders",
            "action": "drop_duplicate_pk",
            "count": dup_count,
            "reason": "Duplicate feeder_id (e.g. CMI-F18) kept first deterministic occurrence.",
        })

    audit_events.extend([
        {
            "table": "feeders",
            "action": "convert_length_metres_to_km",
            "count": int(len_metres_mask.sum()),
            "reason": "Divided feeder lengths > 1000 (entered in metres) by 1000 to obtain km.",
        },
        {
            "table": "feeders",
            "action": "impute_missing_customers_served",
            "count": int(df["is_customers_served_imputed"].sum()),
            "reason": "Imputed missing feeder customers_served with same area_type median (raw preserved).",
        },
    ])
    if inst_be.sum() > 0:
        audit_events.append({
            "table": "feeders",
            "action": "normalize_buddhist_era_year",
            "count": int(inst_be.sum()),
            "reason": "Converted install_year >= 2400 from BE to CE.",
        })
    assert len(df) + dup_count == raw_count
    return df.sort_values("feeder_id").reset_index(drop=True)


def _clean_weather(raw_weather: pd.DataFrame, audit_events: list[dict[str, Any]]) -> pd.DataFrame:
    df = standardize_columns(raw_weather)
    raw_count = len(df)

    parsed_date, date_be = parse_flexible_datetime(df["date"])
    df["date"] = parsed_date.dt.normalize()
    df["province"] = canonicalize_with_map(df["province"], PROVINCE_ALIASES)

    df["rainfall_mm_raw"] = pd.to_numeric(clean_str_series(df["rainfall_mm"]), errors="coerce")
    rain_sentinel_mask = df["rainfall_mm_raw"].notna() & (df["rainfall_mm_raw"] < 0)
    df["rainfall_mm"] = df["rainfall_mm_raw"].mask(rain_sentinel_mask, np.nan)
    df["is_rainfall_sentinel_cleaned"] = rain_sentinel_mask

    df["max_temp_c_raw"] = pd.to_numeric(clean_str_series(df["max_temp_c"]), errors="coerce")
    # Temperatures > 50°C (e.g. Lamphun Jun-Jul 2023 in 84-95.5 range) were recorded in Fahrenheit
    temp_f_mask = df["max_temp_c_raw"].notna() & (df["max_temp_c_raw"] > 50.0)
    df["max_temp_c"] = df["max_temp_c_raw"].where(
        ~temp_f_mask, ((df["max_temp_c_raw"] - 32.0) * (5.0 / 9.0)).round(2)
    )
    df["is_temp_converted_from_f"] = temp_f_mask

    df["max_wind_kmh"] = pd.to_numeric(clean_str_series(df["max_wind_kmh"]), errors="coerce")
    df["thunderstorm"] = parse_boolean_series(df["thunderstorm"])

    df["_non_null_score"] = df[["rainfall_mm", "max_temp_c", "max_wind_kmh", "thunderstorm"]].notna().sum(axis=1)
    df = df.sort_values(["date", "province", "_non_null_score"], ascending=[True, True, False])
    dup_mask = df.duplicated(subset=["date", "province"], keep="first") & df["date"].notna() & df["province"].notna()
    dup_count = int(dup_mask.sum())
    df = df.loc[~dup_mask].drop(columns=["_non_null_score"]).copy()

    if dup_count > 0:
        audit_events.append({
            "table": "weather_daily",
            "action": "drop_duplicate_date_province",
            "count": dup_count,
            "reason": "Duplicate (date, province) kept most complete record deterministically.",
        })
    audit_events.extend([
        {
            "table": "weather_daily",
            "action": "convert_fahrenheit_to_celsius",
            "count": int(df["is_temp_converted_from_f"].sum()),
            "reason": "Converted max_temp_c > 50 (Fahrenheit readings) to Celsius.",
        },
        {
            "table": "weather_daily",
            "action": "replace_negative_rainfall_sentinel_with_na",
            "count": int(df["is_rainfall_sentinel_cleaned"].sum()),
            "reason": "Replaced negative rainfall sentinel (-999) with NaN to avoid biasing averages/correlations.",
        },
    ])
    if date_be.sum() > 0:
        audit_events.append({
            "table": "weather_daily",
            "action": "normalize_buddhist_era_date",
            "count": int(date_be.sum()),
            "reason": "Converted weather date >= 2400 from BE to CE.",
        })
    assert len(df) + dup_count == raw_count
    return df.sort_values(["date", "province"]).reset_index(drop=True)


def _repair_typo_years(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Repair start_time years outside 2023-2024 using outage_id or end_time year."""
    start_ts = df["start_time"].copy()
    end_ts = df["end_time"]
    repaired_mask = pd.Series(False, index=df.index)

    for idx in df.index:
        st = start_ts.at[idx]
        if pd.isna(st) or st.year in (2023, 2024):
            continue
        target_year = None
        oid = df.at[idx, "outage_id"]
        if pd.notna(oid):
            m = _OUTAGE_YEAR_RE.match(str(oid))
            if m and int(m.group(1)) in (2023, 2024):
                target_year = int(m.group(1))
        if target_year is None:
            et = end_ts.at[idx]
            if pd.notna(et) and et.year in (2023, 2024):
                target_year = et.year
        if target_year is not None:
            start_ts.at[idx] = st.replace(year=target_year)
            repaired_mask.at[idx] = True

    return start_ts, repaired_mask


def _clean_outages(
    raw_outages: pd.DataFrame,
    feeders_clean: pd.DataFrame,
    audit_events: list[dict[str, Any]],
) -> pd.DataFrame:
    df = standardize_columns(raw_outages)
    raw_count = len(df)

    # 1. Exact duplicate rows (all columns identical)
    exact_dup_mask = df.duplicated(keep="first")
    exact_dup_count = int(exact_dup_mask.sum())
    df = df.loc[~exact_dup_mask].copy()

    # 2. Canonical IDs, text fields, and numeric parsing
    df["outage_id"] = clean_str_series(df["outage_id"]).str.upper()
    df["feeder_id_raw"] = clean_str_series(df["feeder_id"])
    df["feeder_id"] = normalize_feeder_id(df["feeder_id"])
    feeder_norm_changed = int((df["feeder_id_raw"].notna() & (df["feeder_id_raw"] != df["feeder_id"])).sum())

    df["start_time"], start_be = parse_flexible_datetime(df["start_time"])
    df["end_time"], end_be = parse_flexible_datetime(df["end_time"])

    # 3. Repair typo years (e.g. 2014, 2042, 2204)
    df["start_time"], year_repaired_mask = _repair_typo_years(df)

    # 4. Fix swapped start_time / end_time
    swapped_mask = df["start_time"].notna() & df["end_time"].notna() & (df["end_time"] < df["start_time"])
    if swapped_mask.any():
        orig_start = df.loc[swapped_mask, "start_time"].copy()
        df.loc[swapped_mask, "start_time"] = df.loc[swapped_mask, "end_time"]
        df.loc[swapped_mask, "end_time"] = orig_start
    df["is_swapped_timestamps"] = swapped_mask

    # 5. Duration cleaning: strip placeholders (>= 9999), fix hours->minutes, back-calculate missing
    df["duration_min_raw"] = pd.to_numeric(clean_str_series(df["duration_min"]), errors="coerce")
    placeholder_mask = df["duration_min_raw"].notna() & (df["duration_min_raw"] >= 9999)
    dur_work = df["duration_min_raw"].abs().mask(placeholder_mask, np.nan)

    calc_dur = (df["end_time"] - df["start_time"]).dt.total_seconds() / 60.0
    valid_calc = calc_dur.notna() & (calc_dur > 0)
    hours_mask = (
        dur_work.notna()
        & valid_calc
        & ((dur_work * 60.0 - calc_dur).abs() <= 3.5)
        & (dur_work < calc_dur - 1.0)
    )
    dur_recovered_mask = dur_work.isna() & valid_calc
    dur_clean = np.where(valid_calc, calc_dur.round(2), dur_work)
    df["duration_min"] = pd.Series(dur_clean, index=df.index, dtype="float64")
    df["is_placeholder_duration"] = placeholder_mask
    df["is_duration_in_hours_fixed"] = hours_mask
    df["is_duration_recovered"] = dur_recovered_mask

    # Recover missing end_time when start_time & duration_min are valid
    missing_end_mask = df["end_time"].isna() & df["start_time"].notna() & df["duration_min"].notna() & (df["duration_min"] > 0)
    df.loc[missing_end_mask, "end_time"] = df.loc[missing_end_mask, "start_time"] + pd.to_timedelta(
        df.loc[missing_end_mask, "duration_min"], unit="m"
    )
    df["is_end_time_recovered"] = missing_end_mask

    # 6. Standardize categories & numbers
    df["cause_raw"] = clean_str_series(df["cause"])
    df["cause"] = canonicalize_with_map(df["cause"], CAUSE_ALIASES, default_value="unknown")
    df["outage_type"] = canonicalize_with_map(df["outage_type"], OUTAGE_TYPE_ALIASES)
    df["report_channel"] = canonicalize_title(df["report_channel"])

    df["crew_arrival_min_raw"] = pd.to_numeric(clean_str_series(df["crew_arrival_min"]), errors="coerce")
    neg_crew_mask = df["crew_arrival_min_raw"].notna() & (df["crew_arrival_min_raw"] < 0)
    df["crew_arrival_min"] = df["crew_arrival_min_raw"].mask(neg_crew_mask, np.nan)
    df["is_negative_crew_arrival_cleaned"] = neg_crew_mask

    df["customers_affected_raw"] = parse_comma_numeric(df["customers_affected"])

    # 7. Deduplicate exact duplicate outage_id AND business-key duplicates (feeder_id + start_time)
    # Prefer OUT-2023/2024-... over OUT-CC-... and prefer most complete rows
    df["_is_primary_id"] = ~df["outage_id"].fillna("").str.startswith("OUT-CC-")
    df["_completeness_score"] = (
        df[["feeder_id", "start_time", "end_time", "duration_min", "customers_affected_raw", "cause", "outage_type"]]
        .notna()
        .sum(axis=1)
    )
    df = df.sort_values(
        ["feeder_id", "start_time", "_is_primary_id", "_completeness_score", "outage_id"],
        ascending=[True, True, False, False, True],
        kind="mergesort",
    )

    dup_pk_mask = df["outage_id"].notna() & df["outage_id"].duplicated(keep="first")
    dup_pk_count = int(dup_pk_mask.sum())
    df = df.loc[~dup_pk_mask].copy()

    bk_dup_mask = (
        df["feeder_id"].notna()
        & df["start_time"].notna()
        & df.duplicated(subset=["feeder_id", "start_time"], keep="first")
    )
    bk_dup_count = int(bk_dup_mask.sum())
    df = df.loc[~bk_dup_mask].drop(columns=["_is_primary_id", "_completeness_score"]).copy()

    # 8. Map feeder customers_served & handle exaggerated / missing customers_affected
    feeder_cust_map = feeders_clean.set_index("feeder_id")["customers_served"].to_dict()
    feeder_area_map = feeders_clean.set_index("feeder_id")["area_type"].to_dict()
    valid_feeders = set(feeders_clean["feeder_id"].dropna())
    df["feeder_customers_served"] = df["feeder_id"].map(feeder_cust_map)
    df["_area_tmp"] = df["feeder_id"].map(feeder_area_map)
    df["is_orphan_feeder"] = df["feeder_id"].isna() | ~df["feeder_id"].isin(valid_feeders)

    exceed_mask = (
        df["customers_affected_raw"].notna()
        & df["feeder_customers_served"].notna()
        & (df["customers_affected_raw"] > df["feeder_customers_served"])
    )
    non_pos_cust_mask = df["customers_affected_raw"].notna() & (df["customers_affected_raw"] <= 0)
    missing_cust_mask = df["customers_affected_raw"].isna()

    # Compute valid (non-exaggerated, positive) median per (feeder_id, outage_type), then feeder_id, then area_type
    valid_cust_rows = df.loc[
        df["customers_affected_raw"].notna()
        & (~exceed_mask)
        & (~non_pos_cust_mask)
    ]
    feeder_type_med_cust = valid_cust_rows.groupby(["feeder_id", "outage_type"])["customers_affected_raw"].median().to_dict()
    feeder_med_cust = valid_cust_rows.groupby("feeder_id")["customers_affected_raw"].median().to_dict()
    area_med_cust = valid_cust_rows.groupby("_area_tmp")["customers_affected_raw"].median().to_dict()
    global_med_cust = float(valid_cust_rows["customers_affected_raw"].median()) if not valid_cust_rows.empty else 0.0

    fallback_cust = pd.Series(
        [
            feeder_type_med_cust.get((fid, otype), feeder_med_cust.get(fid, area_med_cust.get(area, global_med_cust)))
            for fid, otype, area in zip(df["feeder_id"], df["outage_type"], df["_area_tmp"])
        ],
        index=df.index,
        dtype="float64",
    ).round()

    df["is_customers_exceed_feeder"] = exceed_mask
    df["is_customers_missing"] = missing_cust_mask | non_pos_cust_mask

    # Cleaned customers_affected: replace exaggerated (> feeder) with feeder median, keep missing as NaN
    # Also compute customers_affected_imputed (fills missing as well) and customers_affected_capped (caps at 100% feeder)
    df["customers_affected"] = df["customers_affected_raw"].where(~(exceed_mask | non_pos_cust_mask), fallback_cust)
    df["customers_affected_capped"] = df["customers_affected_raw"].where(~exceed_mask, df["feeder_customers_served"].astype("float64"))
    df["customers_affected_imputed"] = df["customers_affected"].where(~df["customers_affected"].isna(), fallback_cust)

    # Imputed duration_min (fills the ~11 rows missing both end_time & duration / placeholder)
    valid_dur_rows = df.loc[df["duration_min"].notna() & (df["duration_min"] > 0)]
    area_cause_med_dur = valid_dur_rows.groupby(["_area_tmp", "cause"])["duration_min"].median().to_dict()
    cause_med_dur = valid_dur_rows.groupby("cause")["duration_min"].median().to_dict()
    global_med_dur = float(valid_dur_rows["duration_min"].median()) if not valid_dur_rows.empty else 0.0

    dur_fallback = pd.Series(
        [
            area_cause_med_dur.get((a, c), cause_med_dur.get(c, global_med_dur))
            for a, c in zip(df["_area_tmp"], df["cause"])
        ],
        index=df.index,
        dtype="float64",
    ).round(1)
    df["duration_min_imputed"] = df["duration_min"].where(df["duration_min"].notna() & (df["duration_min"] > 0), dur_fallback)
    df = df.drop(columns=["_area_tmp"])

    # 9. Window, exclusion, and genuine extreme-event flags (inclusive vs exclusive reporting)
    df["is_outside_window"] = df["start_time"].isna() | (df["start_time"] < DATE_WINDOW_START) | (df["start_time"] > DATE_WINDOW_END)
    df["is_missing_impact_metric"] = df["duration_min"].isna() | (df["duration_min"] <= 0) | df["customers_affected"].isna()
    df["is_excluded_from_strict"] = df["is_outside_window"] | df["is_missing_impact_metric"]

    # Separate genuine statistical extreme events (> Q3 + 3*IQR)
    valid_dur = df.loc[~df["is_excluded_from_strict"], "duration_min"].dropna()
    if not valid_dur.empty:
        q1, q3 = valid_dur.quantile([0.25, 0.75])
        upper_fence = float(q3 + 3.0 * (q3 - q1))
    else:
        upper_fence = float("inf")
    df["is_extreme_event"] = (~df["is_excluded_from_strict"]) & (df["duration_min"] > upper_fence)

    # 10. Derived temporal and impact columns
    df["is_year_repaired"] = year_repaired_mask
    df["year"] = df["start_time"].dt.year.astype("Int64")
    df["month"] = df["start_time"].dt.month.astype("Int64")
    df["year_month"] = df["start_time"].dt.strftime("%Y-%m")
    df["hour"] = df["start_time"].dt.hour.astype("Int64")
    df["start_date"] = df["start_time"].dt.normalize()
    df["customer_minutes"] = df["customers_affected"] * df["duration_min"]
    df["customer_minutes_imputed"] = df["customers_affected_imputed"] * df["duration_min_imputed"]
    df["customer_minutes_raw"] = df["customers_affected_raw"] * df["duration_min_raw"].clip(lower=0)

    audit_events.extend([
        {"table": "outages", "action": "drop_exact_duplicate_rows", "count": exact_dup_count, "reason": "Removed identical duplicate rows across all columns."},
        {"table": "outages", "action": "drop_duplicate_outage_id", "count": dup_pk_count, "reason": "Removed duplicate outage_id keeping most complete row."},
        {"table": "outages", "action": "drop_business_key_duplicates", "count": bk_dup_count, "reason": "Removed cross-channel duplicate incidents sharing (feeder_id, start_time)."},
        {"table": "outages", "action": "normalize_feeder_id_format", "count": feeder_norm_changed, "reason": "Standardized feeder_id casing/hyphen/zero-padding to XXX-FNN."},
        {"table": "outages", "action": "normalize_buddhist_era_timestamps", "count": int((start_be | end_be).sum()), "reason": "Converted dd/mm/YYYY Buddhist Era dates (>= 2400) to Gregorian."},
        {"table": "outages", "action": "repair_typo_years", "count": int(year_repaired_mask.sum()), "reason": "Repaired start_time typo years (2014/2042/2204) using outage_id / end_time year."},
        {"table": "outages", "action": "swap_reversed_timestamps", "count": int(swapped_mask.sum()), "reason": "Swapped start_time and end_time where end_time < start_time."},
        {"table": "outages", "action": "strip_placeholder_durations", "count": int(placeholder_mask.sum()), "reason": "Replaced placeholder duration_min (>= 9999: 9999/99999/14400) with NaN / group median."},
        {"table": "outages", "action": "convert_duration_hours_to_minutes", "count": int(hours_mask.sum()), "reason": "Replaced duration_min entered in hours with (end_time - start_time) in minutes."},
        {"table": "outages", "action": "recover_duration_from_timestamps", "count": int(dur_recovered_mask.sum()), "reason": "Back-calculated missing duration_min from valid timestamps."},
        {"table": "outages", "action": "recover_end_time_from_duration", "count": int(missing_end_mask.sum()), "reason": "Back-calculated missing end_time from start_time + duration_min."},
        {"table": "outages", "action": "replace_exaggerated_customers_exceeding_feeder", "count": int(exceed_mask.sum()), "reason": "Replaced impossible customers_affected > feeder.customers_served with feeder valid median (raw & capped preserved)."},
        {"table": "outages", "action": "clean_negative_crew_arrival", "count": int(neg_crew_mask.sum()), "reason": "Replaced negative crew_arrival_min with NaN."},
        {"table": "outages", "action": "flag_valid_extreme_events", "count": int(df["is_extreme_event"].sum()), "reason": f"Flagged valid high-duration extreme events (> Q3 + 3*IQR = {upper_fence:.2f} min) without removing them."},
    ])

    assert len(df) + exact_dup_count + dup_pk_count + bk_dup_count == raw_count
    return df.sort_values(["start_time", "outage_id"], na_position="last").reset_index(drop=True)


def run_pipeline(raw_dir: Path, clean_dir: Path, sample_dir: Path) -> dict[str, Any]:
    """Execute the full deterministic cleaning + enrichment pipeline and write outputs."""
    raw = load_raw_tables(raw_dir)
    audit_events: list[dict[str, Any]] = []

    substations_clean = _clean_substations(raw["substations"], audit_events)
    feeders_clean = _clean_feeders(
        raw["feeders"],
        set(substations_clean["substation_id"].dropna()),
        audit_events,
    )
    weather_clean = _clean_weather(raw["weather"], audit_events)
    outages_clean = _clean_outages(raw["outages"], feeders_clean, audit_events)

    feeders_join = feeders_clean.drop(columns=["customers_served", "customers_served_raw", "is_orphan_substation"], errors="ignore")
    outages_enriched = (
        outages_clean.merge(feeders_join, on="feeder_id", how="left")
        .merge(
            substations_clean[["substation_id", "substation_name", "capacity_mva", "commissioned_year", "province", "region"]],
            on="substation_id",
            how="left",
        )
        .merge(
            weather_clean[["date", "province", "rainfall_mm", "max_temp_c", "max_wind_kmh", "thunderstorm", "is_temp_converted_from_f", "is_rainfall_sentinel_cleaned"]],
            left_on=["start_date", "province"],
            right_on=["date", "province"],
            how="left",
        )
        .drop(columns=["date"], errors="ignore")
    )

    clean_dir = Path(clean_dir)
    sample_dir = Path(sample_dir)
    clean_dir.mkdir(parents=True, exist_ok=True)
    sample_dir.mkdir(parents=True, exist_ok=True)

    tables = {
        "outages_clean": outages_clean,
        "feeders_clean": feeders_clean,
        "substations_clean": substations_clean,
        "weather_clean": weather_clean,
        "outages_enriched": outages_enriched,
    }
    for name, table in tables.items():
        table.to_parquet(clean_dir / f"{name}.parquet", index=False)
        table.to_csv(clean_dir / f"{name}.csv", index=False, encoding="utf-8-sig")
        table.head(50).to_csv(sample_dir / f"{name}_sample.csv", index=False, encoding="utf-8-sig")

    before_after = {
        "outages": {
            "raw_rows": len(raw["outages"]),
            "clean_rows": len(outages_clean),
            "strict_valid_rows": int((~outages_clean["is_excluded_from_strict"]).sum()),
            "unplanned_clean_rows": int((outages_clean["outage_type"] == "Unplanned").sum()),
            "planned_clean_rows": int((outages_clean["outage_type"] == "Planned").sum()),
            "orphan_feeder_rows": int(outages_clean["is_orphan_feeder"].sum()),
        },
        "feeders": {
            "raw_rows": len(raw["feeders"]),
            "clean_rows": len(feeders_clean),
            "customers_served_raw_sum": int(feeders_clean["customers_served_raw"].dropna().sum()),
            "customers_served_imputed_sum": int(feeders_clean["customers_served"].dropna().sum()),
        },
        "substations": {"raw_rows": len(raw["substations"]), "clean_rows": len(substations_clean)},
        "weather_daily": {"raw_rows": len(raw["weather"]), "clean_rows": len(weather_clean)},
    }
    summary = {"before_after": before_after, "audit_events": audit_events}
    (clean_dir / "audit_log.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Mission A reproducible data cleaning pipeline.")
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--clean-dir", type=Path, default=Path("data/clean"))
    parser.add_argument("--sample-dir", type=Path, default=Path("sample"))
    args = parser.parse_args()

    summary = run_pipeline(args.raw_dir, args.clean_dir, args.sample_dir)
    print(json.dumps(summary["before_after"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
