"""Write the B8.7b.4 local-only materialization preplan.

Inputs:
    b87b3_canonical_source_set.csv, b87b3_svf_scenario_model.csv, and
    b87b3_extraction_feasibility_matrix.csv.
Outputs:
    b87b3_local_only_materialization_preplan.csv.
Saved metrics:
    Future local target patterns, source path/rule, method preplan, user
    authorization requirement, no-commit policy, and caveats. This script is
    preplan-only: it does not create directories, per-cell rasters, svfs.zip,
    manifests, runners, or execution packages.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from v12_b87b3_input_inventory import CLAIM_BOUNDARY, DEFAULT_CONFIG, clean, load_config, out_path, write_csv_rows


def row(
    scenario: str,
    item: str,
    source: str,
    target: str,
    method: str,
    status: str,
    caveat: str,
) -> dict[str, Any]:
    """Build one preplan row."""
    return {
        "scenario": scenario,
        "future_materialization_item": item,
        "source_path_or_rule": source,
        "target_pattern": target,
        "method_preplan": method,
        "materialization_status": status,
        "writes_in_this_lane": "false",
        "requires_user_authorization": "true",
        "commit_policy": "do_not_commit_rasters_or_svfs_zip",
        "caveat": caveat,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def run(config_path: Path = DEFAULT_CONFIG) -> list[dict[str, Any]]:
    """Run materialization preplan generation."""
    config = load_config(config_path)
    root = clean(config["target_b87c_asset_root"]).rstrip("/")
    dsm = clean(config["canonical_dsm_path"])
    cdsm = clean(config["canonical_cdsm_path"])
    base_svf = clean(config["canonical_base_svf_path"])
    overhead = clean(config["expected_overhead_source_path"])
    rows = [
        row(
            "base",
            "dsm_tile",
            dsm,
            f"{root}/<cell_id>/base/dsm.tif",
            "future local-only clip/resample to cell tile extent; no action in B8.7b.3",
            "PREPLAN_ONLY",
            "No raster extraction is performed in this lane.",
        ),
        row(
            "base",
            "cdsm_base_vegetation_tile",
            cdsm,
            f"{root}/<cell_id>/base/cdsm.tif",
            "future local-only clip/resample existing vegetation DSM",
            "PREPLAN_ONLY",
            "Base vegetation DSM remains separate from building DSM.",
        ),
        row(
            "base",
            "svf_base_tile",
            base_svf,
            f"{root}/<cell_id>/base/svf/svfs.zip_or_equivalent",
            "future per-cell/tile SOLWEIG SVF materialization from base geometry or reviewed repackaging method",
            "PREPLAN_ONLY_METHOD_TO_FINALIZE_IN_B87B4",
            "Full-AOI SVF is not itself a per-tile SOLWEIG svfs.zip.",
        ),
        row(
            "base",
            "flat_dem_tile",
            "generate flat DEM tile convention later",
            f"{root}/<cell_id>/base/dem.tif",
            "future local zero/flat DEM tile generation",
            "NOT_APPLICABLE_IN_B87B3",
            "No canonical full DEM is required.",
        ),
        row(
            "overhead_as_canopy",
            "cdsm_overhead_as_canopy_tile",
            f"max({cdsm}, {overhead})",
            f"{root}/<cell_id>/overhead_as_canopy/cdsm.tif",
            "future local-only canopy rasterization/merge using overhead vector and existing vegetation DSM",
            "PREPLAN_ONLY",
            "This is a scenario-specific vegetation/canopy DSM.",
        ),
        row(
            "overhead_as_canopy",
            "svf_overhead_as_canopy_tile",
            "building DSM + max(existing vegetation DSM, overhead canopy)",
            f"{root}/<cell_id>/overhead_as_canopy/svf/svfs.zip_or_equivalent",
            "future scenario-specific SVF materialization; base SVF must not be reused",
            "PREPLAN_ONLY_METHOD_TO_FINALIZE_IN_B87B4",
            "Requires overhead-aware geometry and per-tile SOLWEIG-compatible SVF input.",
        ),
        row(
            "all",
            "grid_geometry_clip_reference",
            clean(config["canonical_grid_path"]),
            f"{root}/<cell_id>/focus_cell.geojson",
            "future local-only vector export of focus cell geometry",
            "PREPLAN_ONLY",
            "Vector export only belongs to a later local-only materialization lane.",
        ),
    ]
    write_csv_rows(
        out_path(config, "b87b3_local_only_materialization_preplan.csv"),
        rows,
        [
            "scenario",
            "future_materialization_item",
            "source_path_or_rule",
            "target_pattern",
            "method_preplan",
            "materialization_status",
            "writes_in_this_lane",
            "requires_user_authorization",
            "commit_policy",
            "caveat",
            "claim_boundary",
        ],
    )
    return rows


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Write the local-only materialization preplan; creates no per-cell "
            "assets, no raster outputs, no manifest, and no runner."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(f"materialization_preplan_rows={len(run(args.config))}")


if __name__ == "__main__":
    main()
