"""Shared schema definitions, raw loaders, and canonicalization helpers."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

DATE_WINDOW_START = pd.Timestamp("2023-01-01 00:00:00")
DATE_WINDOW_END = pd.Timestamp("2024-12-31 23:59:59")
FEEDER_EXPORT_DATE = pd.Timestamp("2025-01-05")

EXPECTED_PROVINCES = ("เชียงใหม่", "ลำพูน", "ลำปาง", "เชียงราย")

RAW_FILES = {
    "outages": "outages_raw.csv",
    "feeders": "feeders.xlsx",
    "substations": "substations.json",
    "weather": "weather_daily.csv",
}

COLUMN_RENAMES: dict[str, str] = {
    "feeder id": "feeder_id",
    "substation": "substation_id",
    "area type": "area_type",
    "length": "length_km",
    "customers": "customers_served",
    "tree cover": "tree_cover",
    "overhead %": "overhead_pct",
    "install year": "install_year",
    "location.province": "province",
    "location.region": "region",
}

PROVINCE_ALIASES: dict[str, str] = {
    "เชียงใหม่": "เชียงใหม่",
    "จ.เชียงใหม่": "เชียงใหม่",
    "จังหวัดเชียงใหม่": "เชียงใหม่",
    "chiang mai": "เชียงใหม่",
    "chiangmai": "เชียงใหม่",
    "cm": "เชียงใหม่",
    "ลำพูน": "ลำพูน",
    "จ.ลำพูน": "ลำพูน",
    "จังหวัดลำพูน": "ลำพูน",
    "lamphun": "ลำพูน",
    "lp": "ลำพูน",
    "ลำปาง": "ลำปาง",
    "จ.ลำปาง": "ลำปาง",
    "จังหวัดลำปาง": "ลำปาง",
    "lampang": "ลำปาง",
    "lg": "ลำปาง",
    "เชียงราย": "เชียงราย",
    "จ.เชียงราย": "เชียงราย",
    "จังหวัดเชียงราย": "เชียงราย",
    "chiang rai": "เชียงราย",
    "chiangrai": "เชียงราย",
    "cr": "เชียงราย",
}

AREA_TYPE_ALIASES: dict[str, str] = {
    "เมือง": "Urban",
    "เขตเมือง": "Urban",
    "urban": "Urban",
    "city": "Urban",
    "ชานเมือง": "Suburban",
    "suburban": "Suburban",
    "semi-urban": "Suburban",
    "ชนบท": "Rural",
    "rural": "Rural",
}

OUTAGE_TYPE_ALIASES: dict[str, str] = {
    "unplanned": "Unplanned",
    "unplan": "Unplanned",
    "ไม่วางแผน": "Unplanned",
    "ไม่ได้วางแผน": "Unplanned",
    "ฉุกเฉิน": "Unplanned",
    "emergency": "Unplanned",
    "forced": "Unplanned",
    "planned": "Planned",
    "plan": "Planned",
    "วางแผน": "Planned",
    "ตามแผน": "Planned",
    "บำรุงรักษา": "Planned",
    "maintenance": "Planned",
}

# Maps the 26 raw cause labels (Thai/English) into 8 canonical categories
CAUSE_ALIASES: dict[str, str] = {
    "ต้นไม้": "tree",
    "ต้นไม้ล้มทับสาย": "tree",
    "กิ่งไม้พาดสาย": "tree",
    "tree": "tree",
    "tree contact": "tree",
    "สัตว์": "animal",
    "นก/กระรอก": "animal",
    "งูพันสาย": "animal",
    "animal": "animal",
    "อุปกรณ์ชำรุด": "equipment",
    "หม้อแปลงชำรุด": "equipment",
    "ลูกถ้วยแตก": "equipment",
    "equipment failure": "equipment",
    "equipment": "equipment",
    "ฟ้าผ่า": "lightning",
    "ฟ้าผ่าสาย": "lightning",
    "lightning": "lightning",
    "รถชนเสา": "vehicle",
    "vehicle": "vehicle",
    "โหลดเกิน": "overload",
    "ไฟเกิน": "overload",
    "overload": "overload",
    "ปฏิบัติงานตามแผน": "planned",
    "ดับไฟตามแผน": "planned",
    "planned work": "planned",
    "planned": "planned",
    "unknown": "unknown",
    "ไม่ทราบสาเหตุ": "unknown",
}

BOOLEAN_MAP: dict[str, bool] = {
    "true": True,
    "1": True,
    "1.0": True,
    "yes": True,
    "y": True,
    "ใช่": True,
    "มี": True,
    "false": False,
    "0": False,
    "0.0": False,
    "no": False,
    "n": False,
    "ไม่ใช่": False,
    "ไม่มี": False,
}

_BE_YMD_RE = re.compile(r"^(\d{4})([-/.])(\d{1,2})\2(\d{1,2})(.*)$")
_DMY_RE = re.compile(r"^(\d{1,2})([-/.])(\d{1,2})\2(\d{4})(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?)?$")
_FEEDER_ID_RE = re.compile(r"^([A-Z]{3})\s*-?\s*F\s*(\d+)$")
_TZ_SUFFIX_RE = re.compile(r"[+-]\d{2}:\d{2}$")


def to_snake_case(name: str) -> str:
    """Convert raw header names to normalized snake_case using explicit mappings."""
    cleaned = re.sub(r"\s+", " ", str(name).strip())
    lower = cleaned.lower()
    if lower in COLUMN_RENAMES:
        return COLUMN_RENAMES[lower]
    snake = re.sub(r"[^a-zA-Z0-9]+", "_", lower).strip("_")
    return snake


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of df with standardized snake_case column names."""
    out = df.copy()
    out.columns = [to_snake_case(col) for col in out.columns]
    return out


def clean_str_series(series: pd.Series) -> pd.Series:
    """Trim whitespace and convert empty/null-like string tokens to pd.NA."""
    s = series.astype("string").str.strip()
    null_tokens = {"", "na", "n/a", "null", "none", "nan", "-", "--", "ไม่ระบุ"}
    lowered = s.str.lower()
    return s.mask(lowered.isin(null_tokens), pd.NA)


def normalize_feeder_id(series: pd.Series) -> pd.Series:
    """Canonicalize feeder IDs such as 'cmi f3' or 'CRIF14' to 'XXX-FNN' format."""
    cleaned = clean_str_series(series).str.upper()

    def _norm(val: Any) -> Any:
        if pd.isna(val):
            return pd.NA
        text = re.sub(r"\s+", "", str(val))
        m = _FEEDER_ID_RE.match(text)
        if m:
            return f"{m.group(1)}-F{int(m.group(2)):02d}"
        return text

    return cleaned.map(_norm).astype("string")


def parse_comma_numeric(series: pd.Series) -> pd.Series:
    """Parse numbers that may contain thousand-separator commas (e.g. '1,250')."""
    cleaned = clean_str_series(series).str.replace(",", "", regex=False)
    return pd.to_numeric(cleaned, errors="coerce")


def parse_numeric_with_unit(series: pd.Series) -> pd.Series:
    """Extract leading float/int from strings like '75 MVA'."""
    cleaned = clean_str_series(series).str.extract(r"([-+]?\d+(?:\.\d+)?)", expand=False)
    return pd.to_numeric(cleaned, errors="coerce")


def canonicalize_with_map(series: pd.Series, alias_map: dict[str, str], default_value: str | None = None) -> pd.Series:
    """Normalize text values using a case-insensitive alias table."""
    cleaned = clean_str_series(series)
    lowered = cleaned.str.lower().str.replace(r"\s+", " ", regex=True)
    mapped = lowered.map(alias_map)
    if default_value is not None:
        return mapped.fillna(default_value)
    return mapped.where(mapped.notna(), cleaned)


def canonicalize_title(series: pd.Series) -> pd.Series:
    """Standardize free-text categories by collapsing spaces and title-casing ASCII labels."""
    cleaned = clean_str_series(series)
    collapsed = cleaned.str.replace(r"\s+", " ", regex=True)
    is_ascii = collapsed.str.match(r"^[\x00-\x7F]+$", na=False)
    return collapsed.where(~is_ascii, collapsed.str.title())


def parse_boolean_series(series: pd.Series) -> pd.Series:
    """Parse heterogeneous boolean representations into nullable pandas boolean dtype."""
    if pd.api.types.is_bool_dtype(series):
        return series.astype("boolean")
    cleaned = clean_str_series(series).str.lower()
    mapped = cleaned.map(BOOLEAN_MAP)
    return mapped.astype("boolean")


def _parse_single_datetime(val: Any) -> tuple[pd.Timestamp | pd.NaT, bool]:
    """Parse ISO (+07:00), YYYY-MM-DD, and DD/MM/YYYY (including Buddhist Era) safely."""
    if val is None or pd.isna(val):
        return pd.NaT, False
    if isinstance(val, pd.Timestamp):
        if val.year >= 2400:
            return val.replace(year=val.year - 543), True
        return val.tz_localize(None) if val.tzinfo else val, False

    text = str(val).strip()
    if not text or text.lower() in {"na", "n/a", "null", "none", "nan", "-", "ไม่ระบุ"}:
        return pd.NaT, False

    # 1. Explicit DD/MM/YYYY [HH:MM[:SS]] (day-first! prevents MM/DD ambiguity)
    m_dmy = _DMY_RE.match(text)
    if m_dmy:
        day, month, raw_year = int(m_dmy.group(1)), int(m_dmy.group(3)), int(m_dmy.group(4))
        hour = int(m_dmy.group(5) or 0)
        minute = int(m_dmy.group(6) or 0)
        second = int(m_dmy.group(7) or 0)
        is_be = raw_year >= 2400
        ce_year = raw_year - 543 if is_be else raw_year
        try:
            return pd.Timestamp(ce_year, month, day, hour, minute, second), is_be
        except ValueError:
            return pd.NaT, is_be

    # 2. YYYY-MM-DD with possible BE year
    m_ymd = _BE_YMD_RE.match(text)
    if m_ymd and int(m_ymd.group(1)) >= 2400:
        ce_year = int(m_ymd.group(1)) - 543
        text = f"{ce_year:04d}-{int(m_ymd.group(3)):02d}-{int(m_ymd.group(4)):02d}{m_ymd.group(5)}"
        is_be = True
    else:
        is_be = False

    # 3. Strip ISO 'T' and local '+07:00' timezone suffix to keep uniform local naive timestamps
    normalized = _TZ_SUFFIX_RE.sub("", text.replace("T", " "))
    ts = pd.to_datetime(normalized, errors="coerce")
    if isinstance(ts, pd.Timestamp) and ts.tzinfo is not None:
        ts = ts.tz_localize(None)
    return ts, is_be


def parse_flexible_datetime(series: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Parse mixed-format and Buddhist-Era datetime strings into pandas Timestamps."""
    parsed_vals: list[Any] = []
    be_flags: list[bool] = []
    for item in series.tolist():
        ts, is_be = _parse_single_datetime(item)
        parsed_vals.append(ts)
        be_flags.append(is_be)
    parsed = pd.Series(parsed_vals, index=series.index, dtype="datetime64[ns]")
    be_mask = pd.Series(be_flags, index=series.index, dtype="bool")
    return parsed, be_mask


def normalize_year_value(series: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Normalize integer year columns, converting Buddhist Era (>= 2400) to Gregorian."""
    num = pd.to_numeric(series, errors="coerce")
    be_mask = num.notna() & (num >= 2400)
    ce = num.where(~be_mask, num - 543).round().astype("Int64")
    return ce, be_mask.fillna(False)


def parse_percentage(series: pd.Series) -> pd.Series:
    """Parse percentage strings (e.g. '85%') or 0-1 proportions into 0-100 float scale."""
    cleaned = clean_str_series(series).str.rstrip("%").str.strip()
    num = pd.to_numeric(cleaned, errors="coerce")
    non_null = num.dropna()
    if not non_null.empty and non_null.max() <= 1.0 and (non_null > 0).any() and (non_null < 1.0).any():
        num = num * 100.0
    return num.astype("float64")


def load_raw_tables(raw_dir: Path) -> dict[str, pd.DataFrame]:
    """Load the four competition raw datasets without mutating source files."""
    raw_dir = Path(raw_dir)
    missing = [fname for fname in RAW_FILES.values() if not (raw_dir / fname).exists()]
    if missing:
        raise FileNotFoundError(
            f"Missing raw dataset file(s) in {raw_dir}: {', '.join(missing)}"
        )

    outages = pd.read_csv(raw_dir / RAW_FILES["outages"], dtype="string", keep_default_na=False)

    excel_path = raw_dir / RAW_FILES["feeders"]
    with pd.ExcelFile(excel_path) as xl:
        sheet_name = "feeders" if "feeders" in xl.sheet_names else xl.sheet_names[0]
        feeders = pd.read_excel(xl, sheet_name=sheet_name, dtype=object)

    with (raw_dir / RAW_FILES["substations"]).open("r", encoding="utf-8") as fh:
        sub_payload = json.load(fh)
    if isinstance(sub_payload, dict):
        list_values = [v for v in sub_payload.values() if isinstance(v, list)]
        sub_records = list_values[0] if list_values else [sub_payload]
    else:
        sub_records = sub_payload
    substations = pd.json_normalize(sub_records)

    weather = pd.read_csv(raw_dir / RAW_FILES["weather"], dtype="string", keep_default_na=False)

    return {
        "outages": outages,
        "feeders": feeders,
        "substations": substations,
        "weather": weather,
    }
