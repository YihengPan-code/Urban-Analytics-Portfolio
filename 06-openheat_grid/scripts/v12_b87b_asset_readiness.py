"""Audit B8.7b local asset readiness from prior compact metadata only.

Inputs:
    configs/v12/systemb_b87b_n300_execution_precheck.yaml, B8.6g3 N300 v4
    candidates, B8.5-F2b/F2d/F5 compact asset and readiness CSVs.
Outputs:
    b87b_asset_source_inventory.csv and b87b_cell_asset_readiness.csv.
Saved metrics:
    Prior asset-source availability, new-candidate overlap with prior asset
    rows, root/path metadata existence, per-cell geometry/SVF/DSM/CDSM/DEM/
    landcover/metforcing/QGIS-template readiness, path-resolution status, and
    blocker level. Raster paths are checked only as strings/metadata inherited
    from compact CSVs; raster contents and svfs.zip contents are never opened.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from v12_b87b_input_inventory import CLAIM_BOUNDARY, DEFAULT_CONFIG, clean
from v12_b87b_input_inventory import load_config, out_path, path_exists_metadata, read_csv_rows, write_csv_rows


@dataclass(frozen=True)
class AssetReadinessResult:
    """B8.7b asset-readiness result."""

    status: str
    new_candidate_count: int
    cells_unknown_local_audit: int
    cells_known_missing: int
    headline: str


SOURCE_KEYS = [
    ("b85_f5_pre_execution_asset_check", "f5_pre_execution_asset_check_path", "prior N150 per-run asset readiness"),
    ("b85_f5_manifest", "f5_manifest_path", "prior N150 execution manifest metadata"),
    ("b85_f5_postrun_validation", "f5_postrun_validation_path", "prior N150 postrun output metadata"),
    ("b85_f2b_asset_remap_table", "f2b_asset_remap_table_path", "prior asset root-remap table"),
    ("b85_f2b_root_candidate_inventory", "f2b_root_candidate_inventory_path", "prior root candidate inventory"),
    ("b85_f2d_asset_status", "f2d_asset_status_path", "prior final asset status table"),
    ("b85_f2d_root_inventory", "f2d_root_inventory_path", "prior local/root inventory"),
]


def unique_cells(rows: list[dict[str, str]]) -> set[str]:
    """Return unique cell IDs in compact rows."""
    return {clean(row.get("cell_id")) for row in rows if clean(row.get("cell_id"))}


def source_inventory_row(
    source_key: str,
    path_key: str,
    source_role: str,
    config: dict[str, Any],
    new_cells: set[str],
) -> dict[str, Any]:
    """Build one prior source inventory row."""
    raw_path = clean(config.get(path_key, ""))
    exists, size = path_exists_metadata(raw_path)
    rows: list[dict[str, str]] = []
    columns: list[str] = []
    status = "WARN_MISSING_OPTIONAL_SOURCE"
    if exists == "yes":
        try:
            rows = read_csv_rows(raw_path)
            columns = list(rows[0].keys()) if rows else []
            status = "PASS_SOURCE_AVAILABLE"
        except Exception as exc:  # pragma: no cover - defensive audit output
            status = f"WARN_READ_ERROR:{exc}"
    source_cells = unique_cells(rows)
    return {
        "source_key": source_key,
        "path": raw_path,
        "source_role": source_role,
        "exists_by_metadata_check": exists,
        "size_bytes": size,
        "row_count": len(rows) if rows else "",
        "column_count": len(columns) if columns else "",
        "unique_cell_count": len(source_cells) if source_cells else "",
        "new_candidate_overlap_count": len(source_cells.intersection(new_cells)) if source_cells else 0,
        "status": status,
        "read_scope": "compact_csv_metadata_only",
        "claim_boundary": CLAIM_BOUNDARY,
    }


def global_status_from_f5_precheck(rows: list[dict[str, str]], column: str, pass_value: str = "yes") -> str:
    """Return a compact global readiness status from F5 pre-execution rows."""
    if not rows:
        return "UNKNOWN_LOCAL_AUDIT_REQUIRED"
    values = {clean(row.get(column)).lower() for row in rows}
    if values == {pass_value.lower()}:
        return f"PASS_PRIOR_F5_{column.upper()}_METADATA_ONLY"
    return f"WARN_PRIOR_F5_{column.upper()}_VALUES={'|'.join(sorted(values))}"


def run(config_path: Path = DEFAULT_CONFIG) -> AssetReadinessResult:
    """Audit local asset readiness without opening raster assets."""
    config = load_config(config_path)
    design = read_csv_rows(config["b86g3_n300_v4_design_path"])
    new_cells = {clean(row.get("cell_id")) for row in design if clean(row.get("cell_id"))}
    source_rows = [source_inventory_row(key, path_key, role, config, new_cells) for key, path_key, role in SOURCE_KEYS]
    write_csv_rows(
        out_path(config, "b87b_asset_source_inventory.csv"),
        source_rows,
        [
            "source_key",
            "path",
            "source_role",
            "exists_by_metadata_check",
            "size_bytes",
            "row_count",
            "column_count",
            "unique_cell_count",
            "new_candidate_overlap_count",
            "status",
            "read_scope",
            "claim_boundary",
        ],
    )

    f5_pre = read_csv_rows(config["f5_pre_execution_asset_check_path"])
    f2d_assets = read_csv_rows(config["f2d_asset_status_path"]) if path_exists_metadata(config["f2d_asset_status_path"])[0] == "yes" else []
    f5_cells = unique_cells(f5_pre)
    f2d_cells = unique_cells(f2d_assets)
    met_status = global_status_from_f5_precheck(f5_pre, "met_forcing_ready")
    qgis_status = global_status_from_f5_precheck(f5_pre, "qgis_manual_check_status", pass_value="PASS")

    cell_rows: list[dict[str, Any]] = []
    unknown_count = 0
    missing_count = 0
    for item in design:
        cell_id = clean(item.get("cell_id"))
        has_prior_cell_asset = cell_id in f5_cells or cell_id in f2d_cells
        if has_prior_cell_asset:
            cell_geometry = "PASS_PRIOR_CELL_ASSET_METADATA_PRESENT"
            svf = "PASS_PRIOR_CELL_ASSET_METADATA_PRESENT"
            dsm = "PASS_PRIOR_CELL_ASSET_METADATA_PRESENT"
            cdsm = "PASS_PRIOR_CELL_ASSET_METADATA_PRESENT"
            dem = "PASS_PRIOR_CELL_ASSET_METADATA_PRESENT"
            path_status = "resolved_from_prior_asset_metadata"
            blocker = "none"
            source_status = "prior metadata row found for cell_id"
        else:
            cell_geometry = "UNKNOWN_LOCAL_AUDIT_REQUIRED"
            svf = "UNKNOWN_LOCAL_AUDIT_REQUIRED"
            dsm = "UNKNOWN_LOCAL_AUDIT_REQUIRED"
            cdsm = "UNKNOWN_LOCAL_AUDIT_REQUIRED"
            dem = "UNKNOWN_LOCAL_AUDIT_REQUIRED"
            path_status = "no_prior_cell_asset_mapping_for_new_candidate"
            blocker = "unknown_not_evaluated"
            source_status = (
                "No prior F5/F2d cell asset row for this new candidate; B8.7b "
                "does not create cell geometry, rasters, SVF, or local runner."
            )
            unknown_count += 1
        if "WARN" in met_status or "UNKNOWN" in met_status or "WARN" in qgis_status or "UNKNOWN" in qgis_status:
            blocker = "execution_precheck_blocker" if blocker == "none" else blocker
        if "MISSING" in source_status:
            missing_count += 1
        cell_rows.append(
            {
                "cell_id": cell_id,
                "cell_geometry_status": cell_geometry,
                "svf_asset_status": svf,
                "dsm_asset_status": dsm,
                "cdsm_asset_status": cdsm,
                "dem_asset_status": dem,
                "landcover_asset_status": "not_declared_in_prior_F5_SOLWEIG_manifest",
                "metforcing_asset_status": met_status,
                "qgis_template_status": qgis_status,
                "source_of_status": source_status,
                "path_resolution_status": path_status,
                "blocker_level": blocker,
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )

    write_csv_rows(
        out_path(config, "b87b_cell_asset_readiness.csv"),
        cell_rows,
        [
            "cell_id",
            "cell_geometry_status",
            "svf_asset_status",
            "dsm_asset_status",
            "cdsm_asset_status",
            "dem_asset_status",
            "landcover_asset_status",
            "metforcing_asset_status",
            "qgis_template_status",
            "source_of_status",
            "path_resolution_status",
            "blocker_level",
            "claim_boundary",
        ],
    )

    if missing_count:
        status = "B87B_PRECHECK_BLOCKED_BY_ASSETS"
    elif unknown_count:
        status = "UNKNOWN_LOCAL_AUDIT_REQUIRED"
    else:
        status = "PASS"
    headline = (
        f"{len(new_cells)} new cells audited from compact metadata; "
        f"{unknown_count} require B8.7c local asset remap/preparation audit; "
        "no raster contents opened."
    )
    return AssetReadinessResult(
        status=status,
        new_candidate_count=len(new_cells),
        cells_unknown_local_audit=unknown_count,
        cells_known_missing=missing_count,
        headline=headline,
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Audit B8.7b local asset readiness by prior compact metadata and "
            "Path.exists/stat only. Does not open raster contents or svfs.zip."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
