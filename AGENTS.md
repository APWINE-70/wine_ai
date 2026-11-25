# Project Knowledge & Agent Guidelines (`wine_ai`)

## Repository & Workspace Overview
- **Local Workspace**: `C:\Apai`
- **Remote Repository**: `https://github.com/APWINE-70/wine_ai.git` (`APWINE-70/wine_ai`, public GitHub repository)
- **Default Branch**: `main` (`init.defaultbranch=main`)
- **Project Domain**: Power Outage Data Analysis Competition ("โจทย์การแข่งขันทักษะการวิเคราะห์ข้อมูล: ไฟฟ้าดับ", fictional company: บริษัท ล้านนาพาวเวอร์ดิสทริบิวชัน จำกัด, covering 4 northern provinces for 2023–2024). See [docs/problem_analysis.md](docs/problem_analysis.md) for the full problem breakdown, dataset schemas, scoring rubric, and planned deliverable structure (`data/raw/`, `data/clean/`, `sample/`, `src/`, `notebooks/`, `docs/`).

## Current Directory Structure
- `AGENTS.md` — Project knowledge and agent working guidelines
- `.gitignore`, `requirements.txt` — Git exclusions and pinned Python dependencies (`pandas==3.1.1`, `numpy==2.5.5`, `openpyxl==3.1.5`, `pyarrow==26.0.1`)
- `data/raw/` — Untouched raw competition files (expected: `outages_raw.csv`, `feeders.xlsx`, `substations.json`, `weather_daily.csv`)
- `data/clean/` — Cleaned Parquet/CSV tables, `audit_log.json`, `quality_audit_summary.json`, and pre-aggregated `dashboard_bundle.json`
- `sample/` — 50-row sample CSV slices for testing
- `src/` — Reproducible pipeline modules:
  - `schema.py` — Shared schemas, raw loaders, Buddhist Era date parsing, and canonicalization maps
  - `audit_quality.py` — Mission N 4-dimension quality audit (`python -m src.audit_quality`)
  - `pipeline.py` & `clean_pipeline.py` — Mission A deterministic cleaning & enrichment pipeline (`python -m src.clean_pipeline` / `python -m src.pipeline`)
  - `metrics.py` — SAIFI/SAIDI/CAIDI dual-reporting calculator & dashboard bundle generator (`python -m src.metrics`)
  - `eda_analysis.py` — Phase 2 (Mission B) statistical EDA, 7 executive question metrics, and `docs/web_analytics.json` generator (`python -m src.eda_analysis`)
  - `export_web_data.py` — Phase 3 web bundle generator (`python -m src.export_web_data` -> `web/src/data/dashboard_data.json`)
- `web/` — Phase 3 Next.js 14.2.25 Static Export dashboard (`output: "export"`, Tailwind CSS, Recharts, Lucide Icons, `ChartWrapper` SSR-safe guard):
  - Build: `cd C:\Apai\web; cmd /c npm run build` (outputs static site to `web/out/`)
  - Dev: `cd C:\Apai\web; cmd /c npm run dev`
  - Production URLs: `https://wineai-one.vercel.app` / `https://wineai-nrt6.vercel.app`
  - Judge Test Account: `judge@lannapower.co.th` / `Lanna2025!`
- `tests/test_pipeline_and_metrics.py` — End-to-end `unittest` suite using synthetic fixtures & real-dataset Phase 1–2 invariants (`python -m unittest discover -s tests -v`)
- `docs/` — Documentation deliverables:
  - `problem_analysis.md` — Detailed analysis of the competition brief, datasets, reliability formulas, and deliverable plan
  - `quality_report.md` — Mission N 4-dimension data quality report
  - `data_dictionary.md` — Full column-level Data Dictionary & before–after comparison table
  - `cleaning_summary.md` — Summary of abnormal/exaggerated value cleanup and SAIFI/SAIDI/CAIDI impact
  - `executive_answers.md` — Phase 2 (Mission B) EDA findings, 5 key insights, and 7 executive answers with limitations
  - `web_analytics.json` — Pre-aggregated Phase 2 analytics JSON ready for Phase 3 dashboard consumption
  - `phase3_dashboard.md` — Phase 3 web dashboard architecture, features, and performance summary
  - `quick_guide.md` — Judge quick guide (test account, 1-min walkthrough, local fallback, Vercel deploy)
  - `phase4_deliverables.md` — Phase 4 packaging, presentation, infographic, and deployment summary
- `deliverables/` — 1-page usage infographic (`infographic_user_manual.{html,pdf,png}`) and 12-slide presentation (`presentation_slides.{md,pdf}`, `slides.html`)
- `scripts/` — `run_local.ps1`, `run_local.bat`, and `build_submission_zip.py` (`lanna_power_outage_submission.zip`)
- `Dockerfile`, `web/vercel.json` — Containerized local fallback and Vercel static export config

## Tech Stack & Commands
- **Python**: `3.14.10` (`pip 26.3`)
- **Node.js**: `v26.13.1` (`npm 11.20.0`; note PowerShell blocks `npm.ps1`, invoke via `cmd /c npm ...` or `npm.cmd`)
- **Run Tests**: `python -m unittest discover -s tests -v`
- **Run Pipeline (once raw files are in `data/raw/`)**:
  ```powershell
  python -m src.audit_quality
  python -m src.pipeline
  python -m src.metrics
  ```

## Environment & Git Configuration
- **OS / Shell**: Windows with PowerShell
- **Git Config** (observed at setup):
  - `user.name`: `Wine`
  - `user.email`: `winekae172@gmail.com`
  - `core.autocrlf`: `true`
  - `pull.rebase`: `false`
  - `credential.helper`: `manager`
  - `http.sslbackend`: `schannel`

## Working Conventions for Agents
- Keep this file updated as the codebase grows (tech stack, directory structure, build/test commands, environment variables, and architectural decisions).
- **Rule Format Note**: Standalone `AGENTS.md` files do not use YAML frontmatter and are loaded automatically for `C:\Apai` and all subdirectories (subject to a 24 KB per-file size limit).
- Before pushing the first commit from a newly initialized repo, set upstream tracking with:
  ```powershell
  git push -u origin main
  ```
- Do not push to `origin` unless explicitly requested by the user.
