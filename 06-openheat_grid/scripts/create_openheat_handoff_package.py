"""
create_openheat_handoff_package.py

Create a handoff ZIP for OpenHeat-ToaPayoh.

Usage from project root:

  python scripts\create_openheat_handoff_package.py --root . --mode docs_scripts
  python scripts\create_openheat_handoff_package.py --root . --mode gpt_sources
  python scripts\create_openheat_handoff_package.py --root . --mode full_light

Modes:
  docs_scripts : all docs, scripts, configs, README, src, tests, requirements, notebooks.
  gpt_sources  : curated small source bundle for uploading into GPT Project / new chat.
  full_light   : docs/scripts/configs/src/tests plus selected outputs/data summaries, excluding heavy rasters and raw bulk files.

This script intentionally excludes heavy generated rasters and SOLWEIG TIFFs by default.
"""
from __future__ import annotations

import argparse
import os
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Iterable

TEXT_EXTS = {
    ".md", ".txt", ".py", ".bat", ".json", ".yaml", ".yml", ".toml", ".cfg", ".ini",
    ".js", ".ipynb", ".csv", ".geojson", ".prj", ".qgz", ".png"
}

HEAVY_EXTS = {
    ".tif", ".tiff", ".aux", ".xml", ".zip", ".pack", ".idx", ".rev", ".obj", ".dbf", ".shp", ".shx", ".cpg"
}

EXCLUDE_DIR_NAMES = {
    ".git", ".pytest_cache", "__pycache__", ".ipynb_checkpoints",
    "node_modules", ".venv", "venv", "env"
}

# Heavy/generated folders. These are excluded unless a specific file is explicitly included.
EXCLUDE_PATH_PARTS = {
    "data/rasters",
    "data/solweig/v09_tiles_overhead_aware",  # contains large UMEP outputs
    "data/solweig/v09_tiles",                 # old tile rasters
    "data/archive/openmeteo_forecast_snapshots",
    "data/raw/hdb3d/hdb3d-data/.git",
}

GPT_SOURCE_FILES = [
    "docs/handoff/OPENHEAT_HANDOFF_CN.md",
    "docs/handoff/NEW_CHAT_PROMPT_CN.md",
    "docs/handoff/GPT_PROJECT_SOURCE_FILES_CN.md",
    "docs/v09_freeze/V09_FREEZE_NOTE_CN.md",
    "docs/v09_freeze/V09_REVISED_FINDINGS_CN.md",
    "docs/v09_freeze/33_V09_BUILDING_DSM_GAP_AUDIT_CN.md",
    "docs/v09_freeze/32_V09_COMPLETE_WORK_RECORD_CN.md",
    "docs/v10/V10_PROJECT_STRUCTURE_CN.md",
    "directory_structure.md",
    "configs/v09_gamma_overhead_aware_config.example.json",
    "configs/v09_beta_config.example.json",
    "configs/v09_alpha_config.example.json",
    "scripts/v09_gamma_check_building_completeness.py",
    "scripts/v09_gamma_check_overhead_structures.py",
    "scripts/v08_hdb3d_to_geojson.py",
    "scripts/v08_clip_buildings_to_aoi.py",
    "scripts/v08_merge_buildings_with_height.py",
    "scripts/v08_rasterize_building_dsm.py",
    "scripts/v07_build_grid_features.py",
    "src/openheat_grid/features.py",
    "src/openheat_grid/geospatial.py",
    "src/openheat_grid/grid.py",
    "src/openheat_forecast/hotspot_engine.py",
]

SELECTED_OUTPUT_PATTERNS = [
    "outputs/v09_alpha_calibration/*.md",
    "outputs/v09_beta_calibration/*.md",
    "outputs/v09_beta_threshold_scan/*.md",
    "outputs/v09_gamma_analysis/*.md",
    "outputs/v09_gamma_analysis/*.csv",
    "outputs/v09_gamma_qa/*.md",
    "outputs/v09_gamma_qa/*.csv",
    "outputs/v09_solweig/*.md",
    "outputs/v09_solweig/*.csv",
    "outputs/v08_umep_with_veg_forecast_live/risk_scenarios/*.md",
    "outputs/v08_umep_with_veg_forecast_live/risk_scenarios/*.csv",
    "outputs/v10_*/*.md",
    "outputs/v10_*/*.csv",
]

SELECTED_DATA_PATTERNS = [
    "data/grid/*.csv",
    "data/grid/*.geojson",
    "data/calibration/*.csv",
    "data/features/v071/*.csv",
    "data/features/v071/*.geojson",
    "data/features_3d/*.geojson",
    "data/features_3d/v10/**/*.geojson",
]


def normalise_rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def is_under_excluded_part(rel: str) -> bool:
    rel_norm = rel.replace("\\", "/")
    return any(rel_norm.startswith(part.rstrip("/") + "/") or rel_norm == part.rstrip("/") for part in EXCLUDE_PATH_PARTS)


def should_skip(path: Path, root: Path, max_mb: float) -> bool:
    rel = normalise_rel(path, root)
    parts = set(Path(rel).parts)
    if parts & EXCLUDE_DIR_NAMES:
        return True
    if is_under_excluded_part(rel):
        return True
    if path.suffix.lower() in HEAVY_EXTS:
        return True
    try:
        if path.stat().st_size > max_mb * 1024 * 1024:
            return True
    except OSError:
        return True
    return False


def iter_files_for_docs_scripts(root: Path, max_mb: float) -> Iterable[Path]:
    include_dirs = ["docs", "scripts", "configs", "src", "tests", "notebooks", "README"]
    include_files = [
        "README_CN.md", "README_V09_BETA_CN.md", "requirements.txt", "requirements_v09_beta.txt",
        "requirements_v07_geospatial.txt", "pyproject.toml", ".gitignore", "backup_conda_explicit.txt", "backup_pip.txt",
    ]
    seen: set[Path] = set()
    for d in include_dirs:
        p = root / d
        if p.exists():
            for f in p.rglob("*"):
                if f.is_file() and not should_skip(f, root, max_mb):
                    seen.add(f)
    for f in include_files:
        p = root / f
        if p.exists() and p.is_file() and not should_skip(p, root, max_mb):
            seen.add(p)
    yield from sorted(seen)


def iter_files_for_full_light(root: Path, max_mb: float) -> Iterable[Path]:
    seen = set(iter_files_for_docs_scripts(root, max_mb))
    import glob
    for pattern in SELECTED_OUTPUT_PATTERNS + SELECTED_DATA_PATTERNS:
        for name in glob.glob(str(root / pattern), recursive=True):
            p = Path(name)
            if p.is_file() and not should_skip(p, root, max_mb):
                seen.add(p)
    yield from sorted(seen)


def iter_files_for_gpt_sources(root: Path, max_mb: float) -> Iterable[Path]:
    seen: set[Path] = set()
    for rel in GPT_SOURCE_FILES:
        p = root / rel
        if p.exists() and p.is_file() and not should_skip(p, root, max_mb):
            seen.add(p)
    yield from sorted(seen)


def create_zip(root: Path, out: Path, mode: str, max_mb: float) -> None:
    root = root.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    if mode == "docs_scripts":
        files = list(iter_files_for_docs_scripts(root, max_mb))
    elif mode == "gpt_sources":
        files = list(iter_files_for_gpt_sources(root, max_mb))
    elif mode == "full_light":
        files = list(iter_files_for_full_light(root, max_mb))
    else:
        raise ValueError(f"Unknown mode: {mode}")

    if not files:
        raise RuntimeError("No files selected. Check --root path and mode.")

    manifest_lines = [
        f"OpenHeat handoff package",
        f"Created: {datetime.now().isoformat(timespec='seconds')}",
        f"Mode: {mode}",
        f"Root: {root}",
        f"File count: {len(files)}",
        "",
        "Files:",
    ]

    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for f in files:
            rel = normalise_rel(f, root)
            z.write(f, arcname=rel)
            try:
                size_kb = f.stat().st_size / 1024
            except OSError:
                size_kb = 0
            manifest_lines.append(f"- {rel} ({size_kb:.1f} KB)")

        z.writestr("HANDOFF_PACKAGE_MANIFEST.txt", "\n".join(manifest_lines))

    print(f"[OK] Wrote {out}")
    print(f"[OK] Mode: {mode}")
    print(f"[OK] Files: {len(files)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="Project root directory")
    parser.add_argument("--mode", default="docs_scripts", choices=["docs_scripts", "gpt_sources", "full_light"])
    parser.add_argument("--out", default=None, help="Output ZIP path")
    parser.add_argument("--max-mb", type=float, default=25.0, help="Skip files larger than this size in MB")
    args = parser.parse_args()

    root = Path(args.root)
    if not root.exists():
        print(f"[ERROR] Root does not exist: {root}", file=sys.stderr)
        sys.exit(1)

    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    out = Path(args.out) if args.out else root / "outputs" / "handovers" / f"openheat_handoff_{args.mode}_{stamp}.zip"
    create_zip(root, out, args.mode, args.max_mb)


if __name__ == "__main__":
    main()
