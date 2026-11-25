"""Mission N: 4-Dimension Data Quality Audit (Completeness, Accuracy, Consistency, Timeliness)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.schema import (
    AREA_TYPE_ALIASES,
    CAUSE_ALIASES,
    DATE_WINDOW_END,
    DATE_WINDOW_START,
    EXPECTED_PROVINCES,
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


def _count_missing_by_col(df: pd.DataFrame) -> dict[str, int]:
    """Count missing/blank values per column after normalizing null-like tokens."""
    counts: dict[str, int] = {}
    for col in df.columns:
        cleaned = clean_str_series(df[col])
        n_miss = int(cleaned.isna().sum())
        if n_miss > 0:
            counts[col] = n_miss
    return counts


def _variant_summary(raw_series: pd.Series, canonical_series: pd.Series) -> dict[str, list[str]]:
    """Return mapping from canonical label -> observed raw variants when >1 raw spelling exists."""
    tmp = pd.DataFrame({"raw": clean_str_series(raw_series), "canon": canonical_series}).dropna()
    grouped = tmp.groupby("canon")["raw"].unique()
    return {
        str(canon): sorted(str(v) for v in variants)
        for canon, variants in grouped.items()
        if len(variants) > 1
    }


def run_quality_audit(raw_dir: Path) -> dict[str, Any]:
    """Inspect all 4 raw tables and return structured 4-dimension quality findings."""
    raw = load_raw_tables(raw_dir)
    outages = standardize_columns(raw["outages"])
    feeders = standardize_columns(raw["feeders"])
    substations = standardize_columns(raw["substations"])
    weather = standardize_columns(raw["weather"])

    start_ts, start_be = parse_flexible_datetime(outages["start_time"])
    end_ts, end_be = parse_flexible_datetime(outages["end_time"])
    dur_num = pd.to_numeric(clean_str_series(outages["duration_min"]), errors="coerce")
    cust_raw_str = clean_str_series(outages["customers_affected"])
    cust_num = parse_comma_numeric(outages["customers_affected"])
    crew_num = pd.to_numeric(clean_str_series(outages["crew_arrival_min"]), errors="coerce")

    feeder_id_raw = clean_str_series(outages["feeder_id"])
    feeder_id_norm = normalize_feeder_id(outages["feeder_id"])
    feeder_id_mst = normalize_feeder_id(feeders["feeder_id"])
    feeder_len_mst = pd.to_numeric(clean_str_series(feeders["length_km"]), errors="coerce")
    feeder_cust_mst = parse_comma_numeric(feeders["customers_served"])
    feeder_cust_map = pd.Series(feeder_cust_mst.values, index=feeder_id_mst).dropna().to_dict()
    mapped_feeder_cust = feeder_id_norm.map(feeder_cust_map)

    sub_id_feeder = clean_str_series(feeders["substation_id"]).str.upper()
    sub_id_mst = clean_str_series(substations["substation_id"]).str.upper()
    cap_mva_num = parse_numeric_with_unit(substations["capacity_mva"])

    prov_sub = canonicalize_with_map(substations["province"], PROVINCE_ALIASES)
    prov_wx = canonicalize_with_map(weather["province"], PROVINCE_ALIASES)
    wx_date, wx_be = parse_flexible_datetime(weather["date"])
    wx_rain = pd.to_numeric(clean_str_series(weather["rainfall_mm"]), errors="coerce")
    wx_temp = pd.to_numeric(clean_str_series(weather["max_temp_c"]), errors="coerce")
    wx_wind = pd.to_numeric(clean_str_series(weather["max_wind_kmh"]), errors="coerce")
    wx_storm = parse_boolean_series(weather["thunderstorm"])

    overhead_pct = parse_percentage(feeders["overhead_pct"])
    install_yr, install_be = normalize_year_value(feeders["install_year"])
    comm_yr, comm_be = normalize_year_value(substations["commissioned_year"])

    # 1. Completeness
    expected_dates = pd.date_range(DATE_WINDOW_START.normalize(), DATE_WINDOW_END.normalize(), freq="D")
    expected_grid = {(d, p) for d in expected_dates for p in EXPECTED_PROVINCES}
    observed_grid = set(
        zip(wx_date.dt.normalize().dropna().tolist(), prov_wx.loc[wx_date.notna()].tolist())
    )
    missing_weather_days = len(expected_grid - observed_grid)

    completeness = {
        "row_counts_raw": {
            "outages_raw": int(len(outages)),
            "feeders": int(len(feeders)),
            "substations": int(len(substations)),
            "weather_daily": int(len(weather)),
        },
        "missing_values_by_table": {
            "outages_raw": _count_missing_by_col(outages),
            "feeders": _count_missing_by_col(feeders),
            "substations": _count_missing_by_col(substations),
            "weather_daily": _count_missing_by_col(weather),
        },
        "outages_missing_both_end_and_duration": int((end_ts.isna() & dur_num.isna()).sum()),
        "weather_expected_province_days": len(expected_grid),
        "weather_observed_unique_province_days": len(observed_grid),
        "weather_missing_province_days": missing_weather_days,
    }

    # 2. Accuracy
    # Check duration anomalies on properly ordered (or swapped-adjusted) timestamps
    start_adj = start_ts.where(~(end_ts < start_ts), end_ts)
    end_adj = end_ts.where(~(end_ts < start_ts), start_ts)
    calc_dur = (end_adj - start_adj).dt.total_seconds() / 60.0
    abs_dur = dur_num.abs()
    dur_in_hours = (
        abs_dur.notna()
        & calc_dur.notna()
        & (calc_dur > 0)
        & ((abs_dur * 60.0 - calc_dur).abs() <= 3.5)
        & (abs_dur < calc_dur - 1.0)
    )
    placeholder_dur = dur_num.notna() & (dur_num >= 9999)

    valid_dur_sample = dur_num[(dur_num > 0) & (dur_num < 9999)].dropna()
    q1, q3 = valid_dur_sample.quantile([0.25, 0.75]) if not valid_dur_sample.empty else (0.0, 0.0)
    iqr = float(q3 - q1)
    upper_iqr_fence = float(q3 + 3.0 * iqr) if iqr > 0 else float("inf")

    accuracy = {
        "outages_unparseable_start_time": int((clean_str_series(outages["start_time"]).notna() & start_ts.isna()).sum()),
        "outages_unparseable_end_time": int((clean_str_series(outages["end_time"]).notna() & end_ts.isna()).sum()),
        "outages_swapped_start_end": int((start_ts.notna() & end_ts.notna() & (end_ts < start_ts)).sum()),
        "outages_negative_duration": int((dur_num.notna() & (dur_num < 0)).sum()),
        "outages_duration_in_hours": int(dur_in_hours.sum()),
        "outages_placeholder_duration_ge_9999": int(placeholder_dur.sum()),
        "outages_negative_or_zero_customers": int((cust_num.notna() & (cust_num <= 0)).sum()),
        "outages_customers_exceed_feeder_total": int(
            (cust_num.notna() & mapped_feeder_cust.notna() & (cust_num > mapped_feeder_cust)).sum()
        ),
        "outages_negative_crew_arrival": int((crew_num.notna() & (crew_num < 0)).sum()),
        "outages_extreme_duration_gt_3x_iqr": int((valid_dur_sample > upper_iqr_fence).sum()),
        "outages_duration_3x_iqr_fence_min": round(upper_iqr_fence, 2) if upper_iqr_fence != float("inf") else None,
        "feeders_length_in_metres_gt_1000": int((feeder_len_mst > 1000).sum()),
        "feeders_invalid_overhead_pct": int((overhead_pct.notna() & ((overhead_pct < 0) | (overhead_pct > 100))).sum()),
        "weather_rainfall_sentinel_negative": int((wx_rain < 0).sum()),
        "weather_temp_fahrenheit_gt_50c": int((wx_temp > 50).sum()),
        "weather_negative_wind": int((wx_wind < 0).sum()),
        "weather_unparseable_thunderstorm": int(
            (clean_str_series(weather["thunderstorm"]).notna() & wx_storm.isna()).sum()
        ),
    }

    # 3. Consistency
    outage_ids = clean_str_series(outages["outage_id"])
    canon_cause = canonicalize_with_map(outages["cause"], CAUSE_ALIASES, default_value="unknown")
    canon_otype = canonicalize_with_map(outages["outage_type"], OUTAGE_TYPE_ALIASES)
    canon_channel = canonicalize_title(outages["report_channel"])
    canon_area = canonicalize_with_map(feeders["area_type"], AREA_TYPE_ALIASES)

    exact_dup_outages = int(outages.duplicated().sum())
    exact_dup_feeders = int(feeders.duplicated().sum())

    # Business-key duplicates after normalizing feeder_id & start_time (excluding exact row dups)
    dedup_exact = outages.loc[~outages.duplicated()].copy()
    dedup_exact["_fid_norm"] = normalize_feeder_id(dedup_exact["feeder_id"])
    dedup_exact["_start_ts"], _ = parse_flexible_datetime(dedup_exact["start_time"])
    bk_dups = int(
        dedup_exact[["_fid_norm", "_start_ts"]].dropna().duplicated(keep="first").sum()
    )

    wx_dup_keys = pd.DataFrame({"date": wx_date.dt.normalize(), "province": prov_wx})
    raw_feeder_format_issues = int((feeder_id_raw.notna() & (feeder_id_raw != feeder_id_norm)).sum())
    comma_customers = int(cust_raw_str.fillna("").str.contains(",", regex=False).sum())

    consistency = {
        "exact_duplicate_outage_rows": exact_dup_outages,
        "duplicate_outage_id_rows": int(outage_ids.dropna().duplicated(keep="first").sum()),
        "business_key_duplicate_rows": bk_dups,
        "feeder_id_format_nonstandard_rows": raw_feeder_format_issues,
        "customers_comma_string_rows": comma_customers,
        "exact_duplicate_feeder_rows": exact_dup_feeders,
        "duplicate_feeder_id_rows": int(feeder_id_mst.dropna().duplicated(keep="first").sum()),
        "duplicate_substation_id_rows": int(sub_id_mst.dropna().duplicated(keep="first").sum()),
        "duplicate_weather_date_province_rows": int(wx_dup_keys.dropna().duplicated(keep="first").sum()),
        "orphan_outage_feeder_ids_after_norm": int(
            (feeder_id_norm.notna() & ~feeder_id_norm.isin(set(feeder_id_mst.dropna()))).sum()
        ),
        "orphan_feeder_substation_ids": int(
            (sub_id_feeder.notna() & ~sub_id_feeder.isin(set(sub_id_mst.dropna()))).sum()
        ),
        "substations_capacity_mva_text_rows": int(
            (clean_str_series(substations["capacity_mva"]).notna() & pd.to_numeric(substations["capacity_mva"], errors="coerce").isna() & cap_mva_num.notna()).sum()
        ),
        "buddhist_era_dates_detected": {
            "outages_start_time": int(start_be.sum()),
            "outages_end_time": int(end_be.sum()),
            "weather_date": int(wx_be.sum()),
            "feeders_install_year": int(install_be.sum()),
            "substations_commissioned_year": int(comm_be.sum()),
        },
        "text_variants_detected": {
            "outages_cause": _variant_summary(outages["cause"], canon_cause),
            "outages_type": _variant_summary(outages["outage_type"], canon_otype),
            "outages_report_channel": _variant_summary(outages["report_channel"], canon_channel),
            "feeders_area_type": _variant_summary(feeders["area_type"], canon_area),
            "weather_province": _variant_summary(weather["province"], prov_wx),
            "substations_province": _variant_summary(substations["province"], prov_sub),
        },
    }

    # 4. Timeliness
    timeliness = {
        "outages_start_before_window": int((start_ts.notna() & (start_ts < DATE_WINDOW_START)).sum()),
        "outages_start_after_window": int((start_ts.notna() & (start_ts > DATE_WINDOW_END)).sum()),
        "weather_date_outside_window": int(
            (wx_date.notna() & ((wx_date < DATE_WINDOW_START) | (wx_date > DATE_WINDOW_END))).sum()
        ),
        "feeders_installed_after_2024": int((install_yr.notna() & (install_yr > 2024)).sum()),
        "substations_commissioned_after_2024": int((comm_yr.notna() & (comm_yr > 2024)).sum()),
    }

    return {
        "completeness": completeness,
        "accuracy": accuracy,
        "consistency": consistency,
        "timeliness": timeliness,
    }


def render_quality_report_markdown(audit: dict[str, Any]) -> str:
    """Render a Mission N 4-dimension markdown report from structured audit counts."""
    comp = audit["completeness"]
    acc = audit["accuracy"]
    cons = audit["consistency"]
    time = audit["timeliness"]
    miss_out = comp["missing_values_by_table"].get("outages_raw", {})

    lines = [
        "# รายงานการตรวจสอบคุณภาพข้อมูล 4 มิติ (Mission N: ICT-DRMC-384B)",
        "",
        "> สร้างอัตโนมัติจากข้อมูลดิบใน `data/raw/` โดยไม่มีการแก้ไขไฟล์ต้นฉบับ (ตรวจสอบก่อนทำ Mission B)",
        "",
        "## 1. สรุปจำนวนแถวดิบตั้งต้นและค่าว่าง",
        "",
        "| ตาราง | จำนวนแถวดิบ | ค่าว่างรายคอลัมน์ |",
        "|---|---:|---|",
    ]
    for tbl, cnt in comp["row_counts_raw"].items():
        miss = comp["missing_values_by_table"].get(tbl, {})
        miss_str = ", ".join(f"`{k}`: {v}" for k, v in miss.items()) if miss else "ไม่พบค่าว่าง"
        lines.append(f"| `{tbl}` | {cnt:,} | {miss_str} |")

    lines.extend([
        "",
        f"- **Weather completeness:** คาดหวัง `{comp['weather_expected_province_days']:,}` province-days (731 วัน × 4 จังหวัด), พบจริงไม่ซ้ำ `{comp['weather_observed_unique_province_days']:,}` และขาดหาย **{comp['weather_missing_province_days']:,}** province-days",
        "",
        "## 2. สรุปปัญหาทั้ง 4 มิติ (จำนวนแถว วิธีตรวจ วิธีแก้ และข้อเสนอต่อระบบต้นทาง)",
        "",
        "| มิติ | ประเภทปัญหา | จำนวนแถว | วิธีตรวจ | วิธีแก้ใน Pipeline | ข้อเสนอแนะถึงเจ้าของระบบต้นทาง |",
        "|---|---|---:|---|---|---|",
        f"| **Completeness** | `outages.end_time` ว่าง | {miss_out.get('end_time', 0):,} | ตรวจค่าว่าง/null token | คำนวณคืนจาก `start_time + duration_min` | SCADA: บังคับบันทึกเวลาปิดงานทุกเหตุการณ์ |",
        f"| **Completeness** | `outages.duration_min` ว่าง | {miss_out.get('duration_min', 0):,} | ตรวจค่าว่าง/null token | คำนวณคืนจาก `end_time - start_time` | SCADA: คำนวณ duration อัตโนมัติจาก timestamp |",
        f"| **Completeness** | ว่างทั้ง `end_time` และ `duration_min` | {comp['outages_missing_both_end_and_duration']:,} | ตรวจร่วม 2 คอลัมน์ | ติดธงและทำ dual reporting (ตัดออก vs impute median) | ระบบรับแจ้งเหตุ: ป้องกันการปิดใบงานโดยไม่มีเวลาสิ้นสุด |",
        f"| **Completeness** | `outages.customers_affected` ว่าง / N/A / - / ไม่ระบุ | {miss_out.get('customers_affected', 0):,} | ตรวจหลัง normalize null tokens | ติดธงและทำ sensitivity check (ตัดออก vs impute median สายป้อน) | ศูนย์รับแจ้งเหตุ: เชื่อมจำนวนลูกค้าจาก GIS ตามจุดตัดไฟ |",
        f"| **Completeness** | `feeders.Customers` ว่าง | {comp['missing_values_by_table'].get('feeders', {}).get('customers_served', 0):,} | ตรวจทะเบียนสายป้อน | ประมาณค่าตามค่ามัธยฐานกลุ่ม Area Type และรายงานผลกระทบต่อ SAIFI | GIS: ตรวจความครบถ้วนของจำนวนมิเตอร์ก่อน export |",
        f"| **Completeness** | ข้อมูลอากาศรายวันขาดหาย (province-days) | {comp['weather_missing_province_days']:,} | Cross-join ปฏิทิน 2023–2024 × 4 จังหวัด | ใช้ Left Join เพื่อไม่ให้เหตุการณ์ไฟดับหล่น | กรมอุตุฯ / ETL: ตั้ง alert และ backfill รายวัน |",
        f"| **Accuracy** | `start_time` / `end_time` สลับกัน (`end < start`) | {acc['outages_swapped_start_end']:,} | ตรวจ `end_time < start_time` | สลับเวลาคืนและคำนวณ duration ใหม่เป็นบวก | ศูนย์รับแจ้งเหตุ: เพิ่ม validation ห้ามเวลาสิ้นสุดน้อยกว่าเริ่ม |",
        f"| **Accuracy** | `duration_min` บันทึกเป็นชั่วโมง | {acc['outages_duration_in_hours']:,} | ตรวจ `(dur * 60) ≈ (end - start)` | แทนที่ด้วย `(end_time - start_time)` หน่วยนาที | ระบบรับแจ้งเหตุ: ระบุหน่วย `(นาที)` ชัดเจนและล็อกการคำนวณ |",
        f"| **Accuracy** | `duration_min` เป็นค่า placeholder/เกินจริง (`>= 9999`) | {acc['outages_placeholder_duration_ge_9999']:,} | ตรวจค่า `9999 / 99999 / 14400` | ล้างเป็น missing แล้วรายงานแบบ Strict vs Imputed | SCADA: ห้ามใช้ค่า `9999` แทนค่าว่าง ให้ใช้ `NULL` |",
        f"| **Accuracy** | `customers_affected` เกินจำนวนลูกค้าทั้งสายป้อน | {acc['outages_customers_exceed_feeder_total']:,} | เทียบ `customers_affected > feeder.Customers` | ล้างค่าเกินจริง (เก็บ raw ไว้) และเทียบผลก่อน–หลังแก้ | SCADA/Call Center: บังคับเพดานไม่เกินจำนวนลูกค้าใน GIS |",
        f"| **Accuracy** | `crew_arrival_min` ติดลบ | {acc['outages_negative_crew_arrival']:,} | ตรวจ `< 0` | แปลงเป็น `NaN` (หมายเหตุ: `crew > duration` เป็นเหตุการณ์จริงเมื่อกู้ระบบผ่าน SCADA ก่อนช่างถึง) | ระบบภาคสนาม: ห้ามเวลาเดินทางติดลบ |",
        f"| **Accuracy** | `feeders.Length` บันทึกเป็นเมตร (`> 1000`) | {acc['feeders_length_in_metres_gt_1000']:,} | ตรวจความยาวสาย `> 1000` กม. | หารด้วย `1,000` แปลงเป็นกิโลเมตร | GIS: บังคับหน่วย `km` ก่อนส่งออก |",
        f"| **Accuracy** | อุณหภูมิลำพูนเป็น °F (`> 50`) | {acc['weather_temp_fahrenheit_gt_50c']:,} | ตรวจ `max_temp_c > 50` (พบช่วง 84–95.5 °F) | แปลง `(F - 32) × 5/9` เป็น °C | กรมอุตุฯ / ETL: ตรวจช่วงค่าและหน่วย °C ก่อน ingest |",
        f"| **Accuracy** | ปริมาณฝน sentinel `-999` | {acc['weather_rainfall_sentinel_negative']:,} | ตรวจ `rainfall_mm < 0` | แทนที่ `-999` ด้วย `NaN` เพื่อไม่ให้บิดเบือนค่าเฉลี่ย/สหสัมพันธ์ | กรมอุตุฯ / ETL: แปลงรหัส error `-999` เป็น `NULL` |",
        f"| **Accuracy** | Extreme duration ที่เกิดจริง (`> Q3 + 3×IQR`) | {acc['outages_extreme_duration_gt_3x_iqr']:,} | Tukey fence ({acc['outages_duration_3x_iqr_fence_min']} นาที) | เก็บไว้ในชุด clean และรายงานคู่ **รวม vs ไม่รวมพายุ** | แยก flag เหตุการณ์ภัยพิบัติระดับจังหวัด |",
        f"| **Consistency** | แถวซ้ำทุกคอลัมน์ใน `outages_raw` | {cons['exact_duplicate_outage_rows']:,} | `duplicated()` ทุกคอลัมน์ | ลบแถวซ้ำแบบ deterministic และบันทึกใน `audit_log.json` | ETL กลาง: ทำ idempotent ingestion |",
        f"| **Consistency** | ซ้ำบน business key (`feeder_id + start_time`) | {cons['business_key_duplicate_rows']:,} | ตรวจซ้ำข้าม `OUT-*` และ `OUT-CC-*` | รวมเหตุการณ์ซ้ำข้ามช่องทางและนับจำนวนใน log | SCADA + Call Center: ผูก Master Incident ID เดียวกัน |",
        f"| **Consistency** | รูปแบบ `feeder_id` ไม่มาตรฐาน | {cons['feeder_id_format_nonstandard_rows']:,} | Regex `^[A-Z]{{3}}-?F(\\d+)$` | แปลงเป็น `XXX-FNN` ก่อนตรวจ FK | ทุกระบบ: ใช้ dropdown รหัสสายป้อนมาตรฐาน |",
        f"| **Consistency** | `feeders` แถวซ้ำ (`CMI-F18`) และ `substations.capacity_mva` มีหน่วยข้อความ | {cons['exact_duplicate_feeder_rows'] + cons['substations_capacity_mva_text_rows']:,} | `duplicated()` บนทะเบียนสายป้อน + regex ตรวจหน่วย | ลบแถวซ้ำ (`55 → 54`) และแยกตัวเลข `75.0` MVA | GIS: บังคับ PK และแยกคอลัมน์หน่วยวัดออกจากตัวเลข |",
        f"| **Consistency** | รหัส FK กำพร้า (`outages.feeder_id` หลัง normalize) | {cons['orphan_outage_feeder_ids_after_norm']:,} | Set difference กับทะเบียนสายป้อน | เก็บเหตุการณ์ไว้และแยก flag สำหรับรายงานระดับสายป้อน vs ทั้งระบบ | GIS/SCADA: บังคับ Referential Integrity |",
        f"| **Consistency** | ปี พ.ศ. (`dd/mm/YYYY` ≥ 2400) | {sum(cons['buddhist_era_dates_detected'].values()):,} | Regex ตรวจปี >= 2400 | แปลง `year - 543` แบบ day-first | ทุกระบบ: ใช้ ISO-8601 ค.ศ. |",
        f"| **Timeliness** | ปีพิมพ์ผิดอยู่นอกช่วงข้อมูล (2014, 2042, 2204) | {time['outages_start_before_window'] + time['outages_start_after_window']:,} | ตรวจ `start_time` นอก 2023–2024 | กู้ปีที่ถูกต้องจาก `outage_id` / `end_time` พร้อมบันทึก flag | ระบบรับแจ้งเหตุ: ล็อกช่วงวันที่รับข้อมูลให้ตรงกับปีปฏิบัติการ |",
        "| **Timeliness** | ทะเบียนสายป้อนส่งออกวันที่ `2025-01-05` หลังสิ้นสุดข้อมูลไฟดับ (`2024-12-31`) | 54 สายป้อน | ตรวจ metadata วันส่งออกและ `install_year` | ระบุเป็นข้อจำกัดเรื่อง snapshot จำนวนลูกค้า `total customers served` | GIS: จัดเก็บ Snapshot จำนวนผู้ใช้ไฟ ณ สิ้นปี (As-of-Year) |",
    ])

    lines.extend(["", "## 3. สรุปคำที่เขียนต่างกัน (Text & Category Variants)", ""])
    for field, mapping in cons.get("text_variants_detected", {}).items():
        if not mapping:
            continue
        lines.append(f"### `{field}`")
        for canon, variants in mapping.items():
            joined = ", ".join(f"`{v}`" for v in variants)
            lines.append(f"- **`{canon}`** ← {joined}")
        lines.append("")

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Mission N 4-dimension data quality audit.")
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--out-json", type=Path, default=Path("data/clean/quality_audit_summary.json"))
    parser.add_argument("--out-md", type=Path, default=Path("docs/quality_report.md"))
    args = parser.parse_args()

    audit = run_quality_audit(args.raw_dir)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")

    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text(render_quality_report_markdown(audit), encoding="utf-8")
    print(f"Quality audit saved to {args.out_json} and {args.out_md}")


if __name__ == "__main__":
    main()
