"""Resolve per-cell B8.7b.1 expected local asset paths.

Inputs:
    configs/v12/systemb_b87b1_local_asset_remap.yaml, B8.7b new-candidate
    sample index, and b87b1_prior_local_root_inventory.csv.
Outputs:
    b87b1_cell_asset_expected_paths.csv.
Saved metrics:
    One expected non-run-ready path row per new candidate, selected/fallback
    local roots, tile-folder candidate, SVF/DSM/CDSM/DEM/landcover glob
    candidates, met forcing root, QGIS manual-check root, output-root candidate,
    resolution method, and claim boundary. This script only uses metadata-safe
    Path.exists/is_dir checks and writes compact CSV output.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from v12_b87b1_input_inventory import CLAIM_BOUNDARY, DEFAULT_CONFIG, clean, config_list, load_config
from v12_b87b1_input_inventory import out_path, path_exists_metadata, read_csv_rows, write_csv_rows


@dataclass(frozen=True)
class CellAssetResolverResult:
    """Per-cell expected path resolver result."""

    status: str
    new_candidate_count: int
    cell_tile_folder_resolved_count: int


def normalize_path(path: str) -> str:
    """Normalize a local path display string."""
    return clean(path).replace("\\", "/").rstrip("/")


def join_path(root: str, *parts: str) -> str:
    """Join path parts for display without creating anything."""
    base = normalize_path(root)
    if not base:
        return ""
    return str(Path(base, *parts)).replace("\\", "/")


def fallback_roots(config: dict[str, Any]) -> dict[str, str]:
    """Return configured fallback roots by root key."""
    roots: dict[str, str] = {}
    for candidate in config_list(config, "prior_local_root_candidates"):
        text = normalize_path(candidate)
        lowered = text.lower()
        if "b87c_n300/assets" in lowered:
            roots["b87c_n300_asset_root"] = text
        elif lowered.endswith("b87c_n300"):
            roots["b87c_n300_output_root"] = text
        elif "b85_f1_tiles" in lowered:
            roots["b85_f1_tiles_root"] = text
        elif "met_forcing/b85_f2c" in lowered:
            roots["b85_f2c_met_forcing_root"] = text
        elif "qgis_checks" in lowered:
            roots["qgis_manual_check_root"] = text
        elif "b85_f5_n150" in lowered:
            roots["prior_f5_run_log_root"] = text
    return roots


def selected_roots(config: dict[str, Any]) -> dict[str, str]:
    """Read selected roots from the local-root inventory."""
    inventory_path = out_path(config, "b87b1_prior_local_root_inventory.csv")
    roots = fallback_roots(config)
    if not inventory_path.exists():
        return roots
    selected: dict[str, str] = {}
    for row in read_csv_rows(inventory_path):
        if clean(row.get("selected_for_resolution")) != "yes":
            continue
        root_key = clean(row.get("root_key"))
        candidate = normalize_path(clean(row.get("candidate_path")))
        if root_key and candidate and root_key not in selected:
            selected[root_key] = candidate
    return {**roots, **selected}


def candidate_tile_folders(roots: dict[str, str], cell_id: str) -> list[str]:
    """Return candidate tile folder paths in priority order."""
    candidates: list[str] = []
    asset_root = roots.get("b87c_n300_asset_root", "")
    b85_root = roots.get("b85_f1_tiles_root", "")
    if asset_root:
        candidates.append(join_path(asset_root, cell_id))
        candidates.append(join_path(asset_root, "tiles", cell_id))
    if b85_root:
        candidates.append(join_path(b85_root, cell_id))
    return [candidate for candidate in candidates if candidate]


def choose_tile_folder(candidates: list[str]) -> tuple[str, str]:
    """Select a tile-folder candidate without creating anything."""
    for candidate in candidates:
        exists, is_dir, _, _, _ = path_exists_metadata(candidate)
        if exists == "yes" and is_dir == "yes":
            return candidate, "metadata_existing_folder"
    if candidates:
        return candidates[0], "auto_candidate_unverified_waiting_local_roots"
    return "", "unresolved_waiting_local_roots"


def glob_pattern(folder: str, pattern: str) -> str:
    """Return a display glob pattern under a candidate folder."""
    if not folder:
        return ""
    return join_path(folder, pattern)


def run(config_path: Path = DEFAULT_CONFIG) -> CellAssetResolverResult:
    """Create expected per-cell asset path mappings."""
    config = load_config(config_path)
    roots = selected_roots(config)
    candidates = read_csv_rows(config["b87b_new_candidate_sample_index_path"])
    rows: list[dict[str, Any]] = []
    resolved_count = 0
    for item in candidates:
        cell_id = clean(item.get("cell_id"))
        tile_candidates = candidate_tile_folders(roots, cell_id)
        tile_folder, method = choose_tile_folder(tile_candidates)
        if method == "metadata_existing_folder":
            resolved_count += 1
        met_root = roots.get("b85_f2c_met_forcing_root", "")
        qgis_root = roots.get("qgis_manual_check_root", "")
        output_root = roots.get("b87c_n300_output_root", "")
        rows.append(
            {
                "cell_id": cell_id,
                "primary_role": clean(item.get("primary_role")),
                "spatial_bin": clean(item.get("spatial_bin")),
                "typology": clean(item.get("typology")),
                "source_closeout_status": clean(item.get("source_closeout_status")),
                "cell_tile_folder_candidate": tile_folder,
                "svf_candidate_pattern": f"{glob_pattern(tile_folder, '*svf*.tif')}|{glob_pattern(tile_folder, '*SVF*.tif')}",
                "dsm_candidate_pattern": f"{glob_pattern(tile_folder, '*dsm*.tif')}|{glob_pattern(tile_folder, '*DSM*.tif')}",
                "cdsm_candidate_pattern": f"{glob_pattern(tile_folder, '*cdsm*.tif')}|{glob_pattern(tile_folder, '*CDSM*.tif')}",
                "dem_candidate_pattern": f"{glob_pattern(tile_folder, '*dem*.tif')}|{glob_pattern(tile_folder, '*DEM*.tif')}",
                "landcover_candidate_pattern": f"{glob_pattern(tile_folder, '*landcover*.tif')}|{glob_pattern(tile_folder, '*lc*.tif')}",
                "met_forcing_root": met_root,
                "qgis_manual_check_root": qgis_root,
                "output_root_candidate": join_path(output_root, cell_id) if output_root else "",
                "resolution_method": method,
                "metadata_only": "true",
                "not_run_ready": "true",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )

    write_csv_rows(
        out_path(config, "b87b1_cell_asset_expected_paths.csv"),
        rows,
        [
            "cell_id",
            "primary_role",
            "spatial_bin",
            "typology",
            "source_closeout_status",
            "cell_tile_folder_candidate",
            "svf_candidate_pattern",
            "dsm_candidate_pattern",
            "cdsm_candidate_pattern",
            "dem_candidate_pattern",
            "landcover_candidate_pattern",
            "met_forcing_root",
            "qgis_manual_check_root",
            "output_root_candidate",
            "resolution_method",
            "metadata_only",
            "not_run_ready",
            "claim_boundary",
        ],
    )
    status = "PASS" if resolved_count == len(candidates) else "WAITING_LOCAL_ROOTS"
    return CellAssetResolverResult(status=status, new_candidate_count=len(candidates), cell_tile_folder_resolved_count=resolved_count)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Resolve B8.7b.1 per-cell expected local asset paths by metadata "
            "checks only. Creates no folders, rasters, manifests, or runners."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
