"""Package competition submission ZIP matching exact Section 5 folder specification."""

from __future__ import annotations

import argparse
from pathlib import Path
import zipfile

REQUIRED_DIRS = ("data/raw", "data/clean", "sample", "src", "docs")
REQUIRED_ROOT_FILES = ("requirements.txt", "Dockerfile", "AGENTS.md")
EXTRA_INCLUDE_DIRS = ("scripts", "tests", "deliverables")


def build_submission_zip(
    repo_root: Path = Path("."),
    out_zip: Path = Path("lanna_power_outage_submission.zip"),
) -> dict[str, int]:
    repo_root = Path(repo_root).resolve()
    out_zip = (repo_root / out_zip) if not out_zip.is_absolute() else out_zip

    missing_dirs = [d for d in REQUIRED_DIRS if not (repo_root / d).is_dir()]
    if missing_dirs:
        raise FileNotFoundError(f"Missing required directories: {', '.join(missing_dirs)}")

    must_have_files = [
        "data/raw/outages_raw.csv",
        "data/raw/feeders.xlsx",
        "data/raw/substations.json",
        "data/raw/weather_daily.csv",
        "data/clean/outages_clean.parquet",
        "data/clean/outages_enriched.parquet",
        "data/clean/audit_log.json",
        "docs/data_dictionary.md",
        "docs/quality_report.md",
        "docs/executive_answers.md",
        "docs/quick_guide.md",
        "requirements.txt",
    ]
    missing_files = [f for f in must_have_files if not (repo_root / f).is_file()]
    if missing_files:
        raise FileNotFoundError(f"Missing required files: {', '.join(missing_files)}")

    file_count = 0
    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel_dir in REQUIRED_DIRS + EXTRA_INCLUDE_DIRS:
            base = repo_root / rel_dir
            if not base.exists():
                continue
            for path in sorted(base.rglob("*")):
                if not path.is_file():
                    continue
                if "__pycache__" in path.parts or path.name == ".gitkeep":
                    continue
                arcname = path.relative_to(repo_root).as_posix()
                zf.write(path, arcname=arcname)
                file_count += 1

        for rel_file in REQUIRED_ROOT_FILES:
            p = repo_root / rel_file
            if p.is_file():
                zf.write(p, arcname=rel_file)
                file_count += 1

        # Include lightweight web source files (excluding node_modules and .next)
        web_dir = repo_root / "web"
        if web_dir.is_dir():
            for path in sorted(web_dir.rglob("*")):
                if not path.is_file():
                    continue
                if any(part in {"node_modules", ".next", "out"} for part in path.parts):
                    continue
                arcname = path.relative_to(repo_root).as_posix()
                zf.write(path, arcname=arcname)
                file_count += 1

    return {"file_count": file_count, "size_bytes": out_zip.stat().st_size}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build competition submission ZIP package.")
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--out-zip", type=Path, default=Path("lanna_power_outage_submission.zip"))
    args = parser.parse_args()

    stats = build_submission_zip(args.repo_root, args.out_zip)
    print(f"Created {args.out_zip} ({stats['file_count']} files, {stats['size_bytes'] / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
