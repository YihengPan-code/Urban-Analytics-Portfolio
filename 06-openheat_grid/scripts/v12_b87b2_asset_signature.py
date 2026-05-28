"""Compute metadata-only asset signatures for discovered folders.

Inputs:
    b87b2_cell_folder_candidates.csv and B8.7b.2 config.
Outputs:
    b87b2_asset_signature_by_folder.csv.
Saved metrics:
    Per-folder SVF/DSM/CDSM/DEM/landcover-like flags, optional asset flags,
    raster-like filename count, total file-size metadata, suffixes seen, and
    matched filename previews. This script uses file names, suffixes, directory
    traversal, and stat size metadata only. It never opens raster contents,
    never uses rasterio/GDAL, and never copies/moves/symlinks assets.
"""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path
from typing import Any

from v12_b87b2_input_inventory import CLAIM_BOUNDARY, DEFAULT_CONFIG, FORBIDDEN_RASTER_SUFFIXES, bool_text, clean
from v12_b87b2_input_inventory import config_list, load_config, out_path, read_csv_rows, repo_path, write_csv_rows

LANDCOVER_LC_RE = re.compile(r"(^|[_\-.])lc($|[_\-.])", re.IGNORECASE)


def should_skip(path_text: str, skip_tokens: list[str]) -> bool:
    """Return true if a path should be skipped by metadata scan."""
    normalized = path_text.replace("\\", "/").lower()
    return any(token.lower() in normalized for token in skip_tokens)


def contains_landcover(name: str) -> bool:
    """Return true when a filename is landcover-like."""
    lowered = name.lower()
    return (
        "landcover" in lowered
        or "land_cover" in lowered
        or "landuse" in lowered
        or "land_use" in lowered
        or bool(LANDCOVER_LC_RE.search(Path(lowered).stem))
    )


def classify_name(name: str) -> dict[str, bool]:
    """Classify an asset filename case-insensitively."""
    lowered = name.lower()
    is_cdsm = "cdsm" in lowered or "canopy_dsm" in lowered
    return {
        "svf": "svf" in lowered or "skyview" in lowered or "sky_view" in lowered,
        "dsm": "dsm" in lowered and not is_cdsm,
        "cdsm": is_cdsm,
        "dem": "dem" in lowered or "dtm" in lowered,
        "landcover": contains_landcover(name),
        "building": "building" in lowered or "bldg" in lowered,
        "vegetation": "vegetation" in lowered or "veg" in lowered or "tree" in lowered or "canopy" in lowered,
        "wallheight": "wallheight" in lowered or "wall_height" in lowered or "wall" in lowered,
    }


def scan_folder(config: dict[str, Any], row: dict[str, str]) -> dict[str, Any]:
    """Compute one folder signature."""
    folder = repo_path(clean(row.get("candidate_folder")))
    max_depth = int(config.get("signature_max_depth", 4))
    skip_tokens = config_list(config, "skip_path_tokens")
    flags = {
        "svf": False,
        "dsm": False,
        "cdsm": False,
        "dem": False,
        "landcover": False,
        "building": False,
        "vegetation": False,
        "wallheight": False,
    }
    raster_like_count = 0
    total_size = 0
    suffixes: set[str] = set()
    matched_names: list[str] = []
    scan_error = ""
    try:
        base_parts = len(folder.resolve().parts)
        for dirpath, dirnames, filenames in os.walk(folder):
            current = Path(dirpath)
            depth = len(current.resolve().parts) - base_parts
            if depth >= max_depth:
                dirnames[:] = []
            else:
                dirnames[:] = [
                    name for name in dirnames if not should_skip(str(current / name), skip_tokens)
                ]
            if should_skip(dirpath, skip_tokens):
                continue
            for filename in filenames:
                file_path = current / filename
                if should_skip(str(file_path), skip_tokens):
                    continue
                suffix = file_path.suffix.lower()
                if suffix:
                    suffixes.add(suffix)
                if suffix in FORBIDDEN_RASTER_SUFFIXES:
                    raster_like_count += 1
                try:
                    total_size += file_path.stat().st_size
                except OSError:
                    pass
                file_flags = classify_name(filename)
                if any(file_flags.values()) and len(matched_names) < 12:
                    matched_names.append(filename)
                for key, value in file_flags.items():
                    flags[key] = flags[key] or value
    except OSError as exc:
        scan_error = clean(exc)
    return {
        "cell_id": clean(row.get("cell_id")),
        "candidate_folder": clean(row.get("candidate_folder")),
        "source_root": clean(row.get("source_root")),
        "root_role": clean(row.get("root_role")),
        "evidence_types": clean(row.get("evidence_types")),
        "has_svf_like": bool_text(flags["svf"]),
        "has_dsm_like": bool_text(flags["dsm"]),
        "has_cdsm_like": bool_text(flags["cdsm"]),
        "has_dem_like": bool_text(flags["dem"]),
        "has_landcover_like": bool_text(flags["landcover"]),
        "has_building_like": bool_text(flags["building"]),
        "has_vegetation_like": bool_text(flags["vegetation"]),
        "has_wallheight_like": bool_text(flags["wallheight"]),
        "raster_like_file_count": raster_like_count,
        "total_size_bytes_metadata": total_size,
        "suffixes_seen": "|".join(sorted(suffixes)),
        "matched_names_preview": "|".join(matched_names),
        "metadata_only": "true",
        "no_raster_opened": "true",
        "scan_error": scan_error,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def unique_candidate_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """De-duplicate candidates by cell and folder path."""
    seen: set[tuple[str, str]] = set()
    unique: list[dict[str, str]] = []
    for row in rows:
        key = (clean(row.get("cell_id")), clean(row.get("candidate_folder")).lower())
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return unique


def run(config_path: Path = DEFAULT_CONFIG) -> list[dict[str, Any]]:
    """Run metadata-only asset signature creation."""
    config = load_config(config_path)
    candidates = unique_candidate_rows(read_csv_rows(out_path(config, "b87b2_cell_folder_candidates.csv")))
    rows = [scan_folder(config, row) for row in candidates]
    rows.sort(key=lambda row: (clean(row.get("cell_id")), clean(row.get("candidate_folder"))))
    write_csv_rows(
        out_path(config, "b87b2_asset_signature_by_folder.csv"),
        rows,
        [
            "cell_id",
            "candidate_folder",
            "source_root",
            "root_role",
            "evidence_types",
            "has_svf_like",
            "has_dsm_like",
            "has_cdsm_like",
            "has_dem_like",
            "has_landcover_like",
            "has_building_like",
            "has_vegetation_like",
            "has_wallheight_like",
            "raster_like_file_count",
            "total_size_bytes_metadata",
            "suffixes_seen",
            "matched_names_preview",
            "metadata_only",
            "no_raster_opened",
            "scan_error",
            "claim_boundary",
        ],
    )
    return rows


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Compute B8.7b.2 asset signatures by metadata only; no raster contents are opened."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(f"asset_signatures={len(run(args.config))}")


if __name__ == "__main__":
    main()
