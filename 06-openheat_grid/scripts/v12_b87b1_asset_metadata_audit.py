"""Audit B8.7b.1 expected local asset paths by metadata only.

Inputs:
    b87b1_cell_asset_expected_paths.csv and
    configs/v12/systemb_b87b1_local_asset_remap.yaml.
Outputs:
    b87b1_cell_asset_metadata_audit.csv.
Saved metrics:
    For each new candidate and required asset kind, path/glob existence status,
    candidate count, matched filename count, filename-only preview, total size
    bytes, suffixes seen, and blocker level. This script never opens raster
    contents: it only uses directory metadata, Path.exists/is_dir/is_file/stat,
    and non-recursive glob metadata.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from v12_b87b1_input_inventory import CLAIM_BOUNDARY, DEFAULT_CONFIG, FORBIDDEN_RASTER_SUFFIXES, clean
from v12_b87b1_input_inventory import load_config, out_path, path_exists_metadata, read_csv_rows, write_csv_rows


@dataclass(frozen=True)
class AssetMetadataAuditResult:
    """Metadata audit result."""

    status: str
    audit_rows: int
    waiting_local_roots: int
    missing_assets: int
    ambiguous_assets: int


RASTER_PATTERNS = {
    "svf": ["*svf*.tif", "*SVF*.tif"],
    "dsm": ["*dsm*.tif", "*DSM*.tif"],
    "cdsm": ["*cdsm*.tif", "*CDSM*.tif"],
    "dem": ["*dem*.tif", "*DEM*.tif"],
    "landcover": ["*landcover*.tif", "*lc*.tif"],
}


def split_patterns(value: str) -> list[str]:
    """Split a pipe-delimited pattern display string."""
    return [clean(part) for part in clean(value).split("|") if clean(part)]


def metadata_glob(folder: str, patterns: list[str]) -> tuple[str, int, list[str], int, list[str], str]:
    """Return metadata-only glob results under a folder."""
    exists, is_dir, _, _, _ = path_exists_metadata(folder)
    if exists != "yes" or is_dir != "yes":
        blocker = "waiting_local_roots" if exists == "unknown" else "missing_asset"
        return exists, 0, [], 0, [], blocker
    folder_path = Path(folder)
    matches: dict[str, Path] = {}
    for pattern in patterns:
        try:
            for item in folder_path.glob(pattern):
                if item.is_file():
                    matches[item.name] = item
        except OSError:
            return "unknown", 0, [], 0, [], "waiting_local_roots"
    names = sorted(matches)
    suffixes = sorted({matches[name].suffix.lower() for name in names})
    total_size = 0
    for name in names:
        try:
            total_size += matches[name].stat().st_size
        except OSError:
            pass
    if not names:
        return "no", 0, [], total_size, suffixes, "missing_asset"
    if len(names) > 1:
        return "yes", len(names), names, total_size, suffixes, "ambiguous_multiple_matches"
    return "yes", len(names), names, total_size, suffixes, "none"


def audit_folder(cell: dict[str, str]) -> dict[str, Any]:
    """Audit the candidate cell tile folder."""
    folder = clean(cell.get("cell_tile_folder_candidate"))
    exists, is_dir, _, _, _ = path_exists_metadata(folder)
    blocker = "none" if exists == "yes" and is_dir == "yes" else "waiting_local_roots"
    if exists == "no" and clean(cell.get("resolution_method")) == "metadata_existing_folder":
        blocker = "missing_asset"
    return make_row(
        cell,
        "cell_tile_folder",
        folder,
        exists,
        1,
        1 if blocker == "none" else 0,
        [Path(folder).name] if blocker == "none" else [],
        "",
        [Path(folder).suffix.lower()] if Path(folder).suffix else [],
        blocker,
    )


def audit_raster_kind(cell: dict[str, str], asset_kind: str) -> dict[str, Any]:
    """Audit one raster-like asset kind by filename/glob metadata only."""
    folder = clean(cell.get("cell_tile_folder_candidate"))
    patterns = RASTER_PATTERNS[asset_kind]
    exists, count, names, total_size, suffixes, blocker = metadata_glob(folder, patterns)
    if clean(cell.get("resolution_method")) != "metadata_existing_folder" and blocker == "missing_asset":
        blocker = "waiting_local_roots"
        exists = "unknown"
    return make_row(
        cell,
        asset_kind,
        "|".join(split_patterns(clean(cell.get(f"{asset_kind}_candidate_pattern")))),
        exists,
        len(patterns),
        count,
        names,
        total_size,
        suffixes,
        blocker,
    )


def audit_met_forcing(cell: dict[str, str]) -> dict[str, Any]:
    """Audit the met forcing root by metadata only."""
    root = clean(cell.get("met_forcing_root"))
    exists, is_dir, _, _, _ = path_exists_metadata(root)
    names: list[str] = []
    suffixes: list[str] = []
    total_size = 0
    blocker = "none"
    if exists != "yes" or is_dir != "yes":
        blocker = "waiting_local_roots"
    else:
        try:
            files = sorted(path for path in Path(root).glob("*.txt") if path.is_file())
            names = [path.name for path in files]
            suffixes = sorted({path.suffix.lower() for path in files})
            for path in files:
                total_size += path.stat().st_size
        except OSError:
            blocker = "waiting_local_roots"
        if not names and blocker == "none":
            blocker = "missing_asset"
    return make_row(cell, "met_forcing", root, exists, 1, len(names), names, total_size, suffixes, blocker)


def audit_qgis_manual_check(cell: dict[str, str]) -> dict[str, Any]:
    """Audit the QGIS manual check root/file by metadata only."""
    root = clean(cell.get("qgis_manual_check_root"))
    exists, is_dir, _, _, _ = path_exists_metadata(root)
    names: list[str] = []
    total_size = 0
    blocker = "none"
    if exists != "yes" or is_dir != "yes":
        blocker = "waiting_local_roots"
    else:
        try:
            files = sorted(path for path in Path(root).glob("*.txt") if path.is_file())
            names = [path.name for path in files]
            for path in files:
                total_size += path.stat().st_size
        except OSError:
            blocker = "waiting_local_roots"
        if not names and blocker == "none":
            blocker = "missing_asset"
    return make_row(cell, "qgis_manual_check", root, exists, 1, len(names), names, total_size, [".txt"] if names else [], blocker)


def audit_output_root(cell: dict[str, str]) -> dict[str, Any]:
    """Audit selected future output root by metadata only, without creating it."""
    candidate = clean(cell.get("output_root_candidate"))
    root = str(Path(candidate).parent).replace("\\", "/") if candidate else ""
    exists, is_dir, _, _, _ = path_exists_metadata(root)
    blocker = "none" if exists == "yes" and is_dir == "yes" else "waiting_local_roots"
    return make_row(cell, "output_root", candidate, exists, 1, 1 if blocker == "none" else 0, [Path(root).name] if blocker == "none" else [], "", [], blocker)


def make_row(
    cell: dict[str, str],
    asset_kind: str,
    candidate_path_or_pattern: str,
    exists: str,
    candidate_count: int,
    matched_file_count: int,
    names: list[str],
    total_size: int | str,
    suffixes: list[str],
    blocker: str,
) -> dict[str, Any]:
    """Create one metadata-audit row."""
    if suffixes and any(suffix not in FORBIDDEN_RASTER_SUFFIXES and asset_kind in RASTER_PATTERNS for suffix in suffixes):
        blocker = "warning" if blocker == "none" else blocker
    return {
        "cell_id": clean(cell.get("cell_id")),
        "asset_kind": asset_kind,
        "candidate_path_or_pattern": candidate_path_or_pattern,
        "exists_by_metadata_check": exists,
        "candidate_count": candidate_count,
        "matched_file_count": matched_file_count,
        "matched_file_names_preview": "|".join(names[:5]),
        "total_size_bytes": total_size,
        "suffixes_seen": "|".join(suffixes),
        "blocker_level": blocker,
        "metadata_only": "true",
        "not_run_ready": "true",
        "claim_boundary": CLAIM_BOUNDARY,
    }


def run(config_path: Path = DEFAULT_CONFIG) -> AssetMetadataAuditResult:
    """Run per-cell asset metadata audit."""
    config = load_config(config_path)
    cells = read_csv_rows(out_path(config, "b87b1_cell_asset_expected_paths.csv"))
    rows: list[dict[str, Any]] = []
    for cell in cells:
        rows.append(audit_folder(cell))
        for asset_kind in ["svf", "dsm", "cdsm", "dem", "landcover"]:
            rows.append(audit_raster_kind(cell, asset_kind))
        rows.append(audit_met_forcing(cell))
        rows.append(audit_qgis_manual_check(cell))
        rows.append(audit_output_root(cell))

    fieldnames = [
        "cell_id",
        "asset_kind",
        "candidate_path_or_pattern",
        "exists_by_metadata_check",
        "candidate_count",
        "matched_file_count",
        "matched_file_names_preview",
        "total_size_bytes",
        "suffixes_seen",
        "blocker_level",
        "metadata_only",
        "not_run_ready",
        "claim_boundary",
    ]
    write_csv_rows(out_path(config, "b87b1_cell_asset_metadata_audit.csv"), rows, fieldnames)
    waiting = sum(1 for row in rows if clean(row.get("blocker_level")) == "waiting_local_roots")
    missing = sum(1 for row in rows if clean(row.get("blocker_level")) == "missing_asset")
    ambiguous = sum(1 for row in rows if clean(row.get("blocker_level")) == "ambiguous_multiple_matches")
    status = "PASS" if waiting == 0 and missing == 0 and ambiguous == 0 else "WARN"
    return AssetMetadataAuditResult(status=status, audit_rows=len(rows), waiting_local_roots=waiting, missing_assets=missing, ambiguous_assets=ambiguous)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Audit expected B8.7b.1 local asset paths using metadata-only checks. "
            "No raster contents are opened and no local files are copied or created."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
