"""Write the B8.7b.1 local asset path-pattern registry.

Inputs:
    configs/v12/systemb_b87b1_local_asset_remap.yaml.
Outputs:
    b87b1_asset_pattern_registry.csv.
Saved metrics:
    Required asset kinds, candidate path patterns, metadata-only glob scope,
    and non-run-ready guard flags. This registry declares patterns only and
    creates no directories, no rasters, no manifest, and no runner.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from v12_b87b1_input_inventory import CLAIM_BOUNDARY, DEFAULT_CONFIG, load_config, out_path, write_csv_rows


@dataclass(frozen=True)
class AssetPatternResult:
    """Asset pattern registry result."""

    status: str
    pattern_rows: int


def pattern_rows() -> list[dict[str, Any]]:
    """Return the declared non-executable B8.7b.1 candidate path patterns."""
    rows = [
        ("cell_tile_folder", "asset_root_cell", "<asset_root>/<cell_id>/", "folder_exists_metadata"),
        ("cell_tile_folder", "asset_root_tiles_cell", "<asset_root>/tiles/<cell_id>/", "folder_exists_metadata"),
        ("cell_tile_folder", "b85_f1_tiles_cell", "<b85_f1_tiles_root>/<cell_id>/", "folder_exists_metadata"),
        ("svf", "svf_lower", "<cell_tile_folder>/*svf*.tif", "metadata_only_glob_filename"),
        ("svf", "svf_upper", "<cell_tile_folder>/*SVF*.tif", "metadata_only_glob_filename"),
        ("dsm", "dsm_lower", "<cell_tile_folder>/*dsm*.tif", "metadata_only_glob_filename"),
        ("dsm", "dsm_upper", "<cell_tile_folder>/*DSM*.tif", "metadata_only_glob_filename"),
        ("cdsm", "cdsm_lower", "<cell_tile_folder>/*cdsm*.tif", "metadata_only_glob_filename"),
        ("cdsm", "cdsm_upper", "<cell_tile_folder>/*CDSM*.tif", "metadata_only_glob_filename"),
        ("dem", "dem_lower", "<cell_tile_folder>/*dem*.tif", "metadata_only_glob_filename"),
        ("dem", "dem_upper", "<cell_tile_folder>/*DEM*.tif", "metadata_only_glob_filename"),
        ("landcover", "landcover", "<cell_tile_folder>/*landcover*.tif", "metadata_only_glob_filename"),
        ("landcover", "lc", "<cell_tile_folder>/*lc*.tif", "metadata_only_glob_filename"),
        ("met_forcing", "reuse_f5_met_forcing", "<b85_f2c_met_forcing_root>/*.txt", "root_exists_metadata"),
        ("qgis_manual_check", "manual_check_file", "<qgis_manual_check_root>/*.txt", "metadata_only_glob_filename"),
        ("output_root", "b87c_output_cell", "<b87c_output_root>/<cell_id>/", "root_selected_metadata"),
    ]
    return [
        {
            "asset_kind": asset_kind,
            "pattern_id": pattern_id,
            "candidate_pattern": pattern,
            "pattern_scope": scope,
            "metadata_only": "true",
            "not_run_ready": "true",
            "notes": "Declare/check path metadata only; do not create files or open raster contents.",
            "claim_boundary": CLAIM_BOUNDARY,
        }
        for asset_kind, pattern_id, pattern, scope in rows
    ]


def run(config_path: Path = DEFAULT_CONFIG) -> AssetPatternResult:
    """Write the path-pattern registry."""
    config = load_config(config_path)
    rows = pattern_rows()
    write_csv_rows(
        out_path(config, "b87b1_asset_pattern_registry.csv"),
        rows,
        [
            "asset_kind",
            "pattern_id",
            "candidate_pattern",
            "pattern_scope",
            "metadata_only",
            "not_run_ready",
            "notes",
            "claim_boundary",
        ],
    )
    return AssetPatternResult(status="PASS", pattern_rows=len(rows))


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Write non-executable B8.7b.1 local asset pattern registry. "
            "No files, roots, rasters, manifests, or runners are created."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
