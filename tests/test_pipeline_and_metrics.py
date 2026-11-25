"""Automated tests for Mission N audit, Mission A pipeline, and SAIFI/SAIDI/CAIDI metrics."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.audit_quality import render_quality_report_markdown, run_quality_audit
from src.metrics import build_dashboard_bundle, compute_dual_reliability_summary
from src.pipeline import run_pipeline


def _create_synthetic_raw_dir(root: Path) -> Path:
    raw_dir = root / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    # 1. substations.json (nested document structure)
    substations = [
        {
            "substation_id": "SUB01",
            "substation_name": "Chiang Mai North",
            "capacity_mva": 50,
            "commissioned_year": 2555,  # BE year -> 2012
            "location": {"province": "จ.เชียงใหม่", "region": "North"},
        },
        {
            "substation_id": "SUB02",
            "substation_name": "Lampang Central",
            "capacity_mva": 40,
            "commissioned_year": 2015,
            "location": {"province": "Lampang", "region": "North"},
        },
    ]
    (raw_dir / "substations.json").write_text(
        json.dumps(substations, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 2. feeders.xlsx (sheet: feeders) -> total served = 1000 + 1000 = 2000
    feeders_df = pd.DataFrame([
        {
            "Feeder ID": "F01",
            "Substation": "SUB01",
            "Area Type": "เขตเมือง",
            "Length": 12.5,
            "Customers": 1000,
            "Tree Cover": 20,
            "Overhead %": "80%",
            "Install Year": 2560,
        },
        {
            "Feeder ID": "F02",
            "Substation": "SUB02",
            "Area Type": "rural",
            "Length": 45.0,
            "Customers": 1000,
            "Tree Cover": 65,
            "Overhead %": 95,
            "Install Year": 2019,
        },
    ])
    with pd.ExcelWriter(raw_dir / "feeders.xlsx", engine="openpyxl") as writer:
        feeders_df.to_excel(writer, sheet_name="feeders", index=False)

    # 3. weather_daily.csv (partial rows -> missing province-days detected by audit)
    weather_df = pd.DataFrame([
        {"date": "2023-05-10", "province": "เชียงใหม่", "rainfall_mm": 12.4, "max_temp_c": 36.5, "max_wind_kmh": 28, "thunderstorm": "Yes"},
        {"date": "2567-06-15", "province": "ลำปาง", "rainfall_mm": 0.0, "max_temp_c": 38.0, "max_wind_kmh": 15, "thunderstorm": "0"},
        {"date": "2024-06-15", "province": "ลำปาง", "rainfall_mm": 0.0, "max_temp_c": 38.0, "max_wind_kmh": 15, "thunderstorm": "0"},
    ])
    weather_df.to_csv(raw_dir / "weather_daily.csv", index=False, encoding="utf-8")

    # 4. outages_raw.csv (covers BE dates, exact dup, cross-channel dup, missing duration, planned, invalid row)
    outages_df = pd.DataFrame([
        # Valid unplanned 2023: 200 cust * 60 min = 12,000 cust-min
        {
            "outage_id": "OUT001",
            "feeder_id": "F01",
            "start_time": "2023-05-10 14:00:00",
            "end_time": "2023-05-10 15:00:00",
            "duration_min": 60,
            "customers_affected": 200,
            "cause": "tree",
            "outage_type": "ไม่ได้วางแผน",
            "report_channel": "scada",
            "crew_arrival_min": 20,
        },
        # Exact duplicate of OUT001 (should be deduplicated and logged)
        {
            "outage_id": "OUT001",
            "feeder_id": "F01",
            "start_time": "2023-05-10 14:00:00",
            "end_time": "2023-05-10 15:00:00",
            "duration_min": 60,
            "customers_affected": 200,
            "cause": "Tree",
            "outage_type": "Unplanned",
            "report_channel": "scada",
            "crew_arrival_min": 20,
        },
        # Valid unplanned 2023 with missing duration_min recoverable from timestamps (30 min), BE date
        {
            "outage_id": "OUT002",
            "feeder_id": "F02",
            "start_time": "2566-08-01 10:00:00",
            "end_time": "2566-08-01 10:30:00",
            "duration_min": "",
            "customers_affected": 400,
            "cause": "equipment failure",
            "outage_type": "Unplanned",
            "report_channel": "call center",
            "crew_arrival_min": 15,
        },
        # Planned outage in 2023 (MUST be excluded from SAIFI/SAIDI)
        {
            "outage_id": "OUT003",
            "feeder_id": "F01",
            "start_time": "2023-09-01 09:00:00",
            "end_time": "2023-09-01 12:00:00",
            "duration_min": 180,
            "customers_affected": 500,
            "cause": "maintenance",
            "outage_type": "Planned",
            "report_channel": "ops",
            "crew_arrival_min": 0,
        },
        # Valid unplanned 2024: 500 cust * 40 min = 20,000 cust-min
        {
            "outage_id": "OUT004",
            "feeder_id": "F02",
            "start_time": "2024-06-15 18:00:00",
            "end_time": "2024-06-15 18:40:00",
            "duration_min": 40,
            "customers_affected": 500,
            "cause": "storm",
            "outage_type": "Unplanned",
            "report_channel": "SCADA",
            "crew_arrival_min": 25,
        },
        # Invalid unplanned 2024 (customers_affected > feeder.Customers 1000) -> flagged for dual reporting
        {
            "outage_id": "OUT005",
            "feeder_id": "F01",
            "start_time": "2024-07-01 12:00:00",
            "end_time": "2024-07-01 12:20:00",
            "duration_min": 20,
            "customers_affected": 1500,
            "cause": "animal",
            "outage_type": "Unplanned",
            "report_channel": "call center",
            "crew_arrival_min": 10,
        },
    ])
    outages_df.to_csv(raw_dir / "outages_raw.csv", index=False, encoding="utf-8")
    return raw_dir


class PipelineAndMetricsTests(unittest.TestCase):
    def test_audit_pipeline_reproducibility_and_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw_dir = _create_synthetic_raw_dir(root)
            clean_dir = root / "clean"
            sample_dir = root / "sample"

            # 1. Mission N Audit
            audit = run_quality_audit(raw_dir)
            self.assertEqual(audit["completeness"]["row_counts_raw"]["outages_raw"], 6)
            self.assertEqual(audit["consistency"]["duplicate_outage_id_rows"], 1)
            self.assertEqual(audit["accuracy"]["outages_customers_exceed_feeder_total"], 1)
            self.assertGreater(audit["completeness"]["weather_missing_province_days"], 0)
            md = render_quality_report_markdown(audit)
            self.assertIn("Completeness", md)
            self.assertIn("Timeliness", md)

            # 2. Mission A Pipeline (Run twice to verify determinism)
            summary1 = run_pipeline(raw_dir, clean_dir, sample_dir)
            hash1 = hashlib.sha256((clean_dir / "outages_enriched.csv").read_bytes()).hexdigest()

            summary2 = run_pipeline(raw_dir, clean_dir, sample_dir)
            hash2 = hashlib.sha256((clean_dir / "outages_enriched.csv").read_bytes()).hexdigest()

            self.assertEqual(hash1, hash2)
            self.assertEqual(summary1["before_after"]["outages"]["raw_rows"], 6)
            self.assertEqual(summary1["before_after"]["outages"]["clean_rows"], 5)
            self.assertEqual(summary1["before_after"]["outages"]["strict_valid_rows"], 5)
            self.assertTrue((sample_dir / "outages_enriched_sample.csv").exists())

            # 3. Reliability indices (SAIFI/SAIDI/CAIDI) & dual reporting
            outages_clean = pd.read_parquet(clean_dir / "outages_clean.parquet")
            feeders_clean = pd.read_parquet(clean_dir / "feeders_clean.parquet")
            rel = compute_dual_reliability_summary(outages_clean, feeders_clean)

            # Total served = 2000
            # 2023 strict unplanned: OUT001 (200*60=12000) + OUT002 (400*30=12000) = 600 cust, 24000 cust-min
            # SAIFI 2023 = 600/2000 = 0.3, SAIDI 2023 = 24000/2000 = 12.0, CAIDI = 40.0
            m23 = rel["scenarios"]["strict_clean"]["2023"]
            self.assertEqual(m23["outage_count"], 2)  # Planned OUT003 excluded!
            self.assertAlmostEqual(m23["saifi"], 0.3, places=4)
            self.assertAlmostEqual(m23["saidi"], 12.0, places=4)
            self.assertAlmostEqual(m23["caidi"], 40.0, places=4)

            # 2024 strict (excludes nothing except missing/invalid) vs raw_uncleaned (uses uncleaned 1500)
            m24_strict = rel["scenarios"]["strict_clean"]["2024"]
            m24_raw = rel["scenarios"]["raw_uncleaned_unplanned"]["2024"]
            self.assertAlmostEqual(m24_strict["saifi"], (500 + 200) / 2000, places=4)
            self.assertAlmostEqual(m24_strict["saidi"], (500 * 40 + 200 * 20) / 2000, places=4)
            self.assertAlmostEqual(m24_raw["saifi"], (500 + 1500) / 2000, places=4)

            # 4. Dashboard bundle generation
            bundle = build_dashboard_bundle(clean_dir)
            self.assertEqual(bundle["data_cutoff"], "2024-12-31 23:59")
            self.assertTrue((clean_dir / "dashboard_bundle.json").exists())

    @unittest.skipUnless(
        Path("data/raw/outages_raw.csv").exists() and Path("data/clean/outages_clean.parquet").exists(),
        "Real competition datasets not present in data/raw and data/clean",
    )
    def test_real_competition_dataset_phase1_invariants(self) -> None:
        outages = pd.read_parquet("data/clean/outages_clean.parquet")
        feeders = pd.read_parquet("data/clean/feeders_clean.parquet")
        substations = pd.read_parquet("data/clean/substations_clean.parquet")
        weather = pd.read_parquet("data/clean/weather_clean.parquet")

        self.assertEqual(len(outages), 2743)
        self.assertEqual(int((outages["outage_type"] == "Unplanned").sum()), 2594)
        self.assertEqual(int((outages["outage_type"] == "Planned").sum()), 149)
        self.assertEqual(len(feeders), 54)
        self.assertEqual(len(substations), 8)
        self.assertEqual(len(weather), 2899)

        fk_match_rate = float((~outages["is_orphan_feeder"]).mean())
        self.assertAlmostEqual(fk_match_rate, 2733 / 2743, places=4)
        self.assertGreaterEqual(fk_match_rate, 0.9963)

        self.assertFalse((outages["crew_arrival_min"].dropna() < 0).any())
        self.assertFalse((feeders["length_km"] > 1000).any())
        self.assertFalse((weather["max_temp_c"] > 50).any())
        self.assertFalse((weather["rainfall_mm"].dropna() < 0).any())
        self.assertEqual(
            set(outages["cause"].unique()),
            {"tree", "animal", "equipment", "lightning", "vehicle", "overload", "planned", "unknown"},
        )

    @unittest.skipUnless(
        Path("docs/web_analytics.json").exists(),
        "Phase 2 analytics bundle docs/web_analytics.json not present",
    )
    def test_phase2_web_analytics_invariants(self) -> None:
        analytics = json.loads(Path("docs/web_analytics.json").read_text(encoding="utf-8"))
        self.assertEqual(analytics["metadata"]["unplanned_events"], 2594)
        self.assertEqual(analytics["storm_reconciliation_2024_08_22_23"]["storm_event_count"], 79)

        rel = analytics["q1_reliability_overview"]["scenarios"]
        self.assertEqual(rel["clean_imputed_all_unplanned"]["2023"]["outage_count"], 1180)
        self.assertEqual(rel["clean_imputed_all_unplanned"]["2024"]["outage_count"], 1414)
        self.assertEqual(rel["clean_imputed_without_chiang_rai_storm"]["2024"]["outage_count"], 1335)

        top5 = [f["feeder_id"] for f in analytics["q3_feeder_priority"]["top5_feeders"]]
        self.assertEqual(top5, ["CRI-F11", "CRI-F03", "CRI-F04", "LPG-F09", "CRI-F13"])

        alerts = {a["feeder_id"]: a for a in analytics["q3_feeder_priority"]["aging_equipment_alerts"]}
        self.assertIn("CMI-F14", alerts)
        self.assertEqual((alerts["CMI-F14"]["equip_2023"], alerts["CMI-F14"]["equip_2024"]), (5, 19))

        q7 = analytics["q7_three_project_simulation"]
        self.assertEqual(len(q7["projects"]), 3)
        self.assertGreater(q7["estimated_total_saidi_reduction_min"], 0)
        self.assertLess(q7["projected_2024_saidi_min"], q7["baseline_2024_saidi_min"])


if __name__ == "__main__":
    unittest.main()
