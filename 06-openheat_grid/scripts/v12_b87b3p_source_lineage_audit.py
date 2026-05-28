"""Audit source/path lineage parity for B8.7b.3p.

Inputs:
    b87b3p_batch_protocol_matrix.csv from protocol extraction plus configured
    B8.7b.3 source-lock evidence.
Outputs:
    b87b3p_source_path_lineage_matrix.csv,
    b87b3p_dsm_version_parity.csv,
    b87b3p_cdsm_version_parity.csv,
    b87b3p_dem_landcover_parity.csv,
    b87b3p_forcing_design_parity.csv,
    b87b3p_tile_spec_parity.csv,
    b87b3p_solweig_parameter_parity.csv.
Saved metrics:
    Final-N150 versus planned-N300 parity for DSM, CDSM, grid/source paths,
    DEM, landcover, forcing design, tile layout, and SOLWEIG parameters. This
    script reads compact protocol tables only; no QGIS/SOLWEIG, raster pixel
    reads, svfs.zip opens, runner/manifest creation, staging, or commits.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from v12_b87b3p_batch_discovery import ROLE_FINAL, ROLE_PLANNED
from v12_b87b3p_protocol_extractor import run as run_protocol_extractor
from v12_b87b3p_input_inventory import (
    CLAIM_BOUNDARY,
    DEFAULT_CONFIG,
    clean,
    load_config,
    out_path,
    read_csv_rows,
    write_csv_rows,
)


LINEAGE_FIELDS = [
    "source_dimension",
    "criticality",
    "final_n150_value",
    "planned_n300_value",
    "parity_status",
    "blocker_status",
    "evidence",
    "notes",
    "claim_boundary",
]

DSM_FIELDS = [
    "batch_id",
    "role",
    "building_dsm_path",
    "building_dsm_version_status",
    "parity_status",
    "notes",
    "claim_boundary",
]

CDSM_FIELDS = [
    "batch_id",
    "role",
    "vegetation_cdsm_path",
    "vegetation_cdsm_version_status",
    "parity_status",
    "notes",
    "claim_boundary",
]

DEM_LC_FIELDS = [
    "batch_id",
    "role",
    "dem_mode",
    "landcover_mode",
    "parity_status",
    "notes",
    "claim_boundary",
]

FORCING_FIELDS = [
    "batch_id",
    "role",
    "forcing_day_id_set",
    "hour_sgt_set",
    "scenarios",
    "parity_status",
    "notes",
    "claim_boundary",
]

TILE_FIELDS = [
    "batch_id",
    "role",
    "tile_spec",
    "per_cell_asset_layout",
    "parity_status",
    "notes",
    "claim_boundary",
]

PARAM_FIELDS = [
    "batch_id",
    "role",
    "qgis_umep_algorithm_id",
    "solweig_parameters",
    "parity_status",
    "notes",
    "claim_boundary",
]


def ensure_protocol_matrix(config: dict[str, Any], config_path: str | Path) -> list[dict[str, str]]:
    """Read protocol matrix, creating it if missing."""
    path = out_path(config, "b87b3p_batch_protocol_matrix.csv")
    if not path.exists():
        run_protocol_extractor(config_path)
    return read_csv_rows(path)


def lookup(matrix: list[dict[str, str]], role: str, dimension_name: str) -> dict[str, str]:
    """Return the first protocol matrix row for a role and dimension."""
    for row in matrix:
        if clean(row.get("role")) == role and clean(row.get("dimension_name")) == dimension_name:
            return row
    return {}


def rows_for_roles(matrix: list[dict[str, str]], dimension_names: list[str]) -> dict[tuple[str, str], dict[str, str]]:
    """Return matrix rows keyed by batch/dimension for selected dimensions."""
    result: dict[tuple[str, str], dict[str, str]] = {}
    for row in matrix:
        if clean(row.get("dimension_name")) in dimension_names:
            result[(clean(row.get("batch_id")), clean(row.get("dimension_name")))] = row
    return result


def final_vs_planned_status(final_row: dict[str, str], planned_row: dict[str, str]) -> tuple[str, str, str]:
    """Classify final versus planned status for a dimension."""
    final_status = clean(final_row.get("parity_status", "UNKNOWN_REQUIRES_REVIEW"))
    final_value = clean(final_row.get("protocol_value", ""))
    planned_value = clean(planned_row.get("protocol_value", ""))
    if final_status.startswith("PASS"):
        return final_status, "not_blocking", clean(final_row.get("parity_note", ""))
    if final_status.startswith("WARN"):
        return final_status, "review_not_blocking_unless_lineage_changed", clean(final_row.get("parity_note", ""))
    if not final_value or not planned_value:
        return "UNKNOWN_REQUIRES_REVIEW", "review_required", "Missing final or planned protocol value."
    return final_status, "review_required", clean(final_row.get("parity_note", ""))


def build_lineage_rows(matrix: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Build source/path lineage rows."""
    dimension_criticality = {
        "building_dsm_path": "core_source",
        "building_dsm_version_status": "core_source",
        "vegetation_cdsm_path": "core_source",
        "vegetation_cdsm_version_status": "core_source",
        "grid_geometry_path": "geometry_source",
        "overhead_layer_path": "core_source",
    }
    rows: list[dict[str, Any]] = []
    for dimension, criticality in dimension_criticality.items():
        final_row = lookup(matrix, ROLE_FINAL, dimension)
        planned_row = lookup(matrix, ROLE_PLANNED, dimension)
        status, blocker, notes = final_vs_planned_status(final_row, planned_row)
        rows.append(
            {
                "source_dimension": dimension,
                "criticality": criticality,
                "final_n150_value": clean(final_row.get("protocol_value", "")),
                "planned_n300_value": clean(planned_row.get("protocol_value", "")),
                "parity_status": status,
                "blocker_status": blocker,
                "evidence": clean(final_row.get("evidence", "")) + ";" + clean(planned_row.get("evidence", "")),
                "notes": notes,
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    return rows


def build_dsm_rows(matrix: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Build DSM version parity rows for every batch."""
    batches = sorted({clean(row.get("batch_id", "")) for row in matrix if clean(row.get("batch_id", ""))})
    rows: list[dict[str, Any]] = []
    for batch_id in batches:
        path_row = next((row for row in matrix if row["batch_id"] == batch_id and row["dimension_name"] == "building_dsm_path"), {})
        status_row = next((row for row in matrix if row["batch_id"] == batch_id and row["dimension_name"] == "building_dsm_version_status"), {})
        rows.append(
            {
                "batch_id": batch_id,
                "role": clean(path_row.get("role", status_row.get("role", ""))),
                "building_dsm_path": clean(path_row.get("protocol_value", "")),
                "building_dsm_version_status": clean(status_row.get("protocol_value", "")),
                "parity_status": clean(path_row.get("parity_status", status_row.get("parity_status", ""))),
                "notes": clean(path_row.get("parity_note", status_row.get("parity_note", ""))),
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    return rows


def build_cdsm_rows(matrix: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Build CDSM version parity rows for every batch."""
    batches = sorted({clean(row.get("batch_id", "")) for row in matrix if clean(row.get("batch_id", ""))})
    rows: list[dict[str, Any]] = []
    for batch_id in batches:
        path_row = next((row for row in matrix if row["batch_id"] == batch_id and row["dimension_name"] == "vegetation_cdsm_path"), {})
        status_row = next((row for row in matrix if row["batch_id"] == batch_id and row["dimension_name"] == "vegetation_cdsm_version_status"), {})
        rows.append(
            {
                "batch_id": batch_id,
                "role": clean(path_row.get("role", status_row.get("role", ""))),
                "vegetation_cdsm_path": clean(path_row.get("protocol_value", "")),
                "vegetation_cdsm_version_status": clean(status_row.get("protocol_value", "")),
                "parity_status": clean(path_row.get("parity_status", status_row.get("parity_status", ""))),
                "notes": clean(path_row.get("parity_note", status_row.get("parity_note", ""))),
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    return rows


def build_dimension_pair_rows(matrix: list[dict[str, str]], dimensions: list[str], fields: list[str]) -> list[dict[str, Any]]:
    """Build compact rows for DEM/LC, forcing, tile, or parameter families."""
    batches = sorted({clean(row.get("batch_id", "")) for row in matrix if clean(row.get("batch_id", ""))})
    rows: list[dict[str, Any]] = []
    for batch_id in batches:
        values = {
            clean(row["dimension_name"]): row
            for row in matrix
            if row["batch_id"] == batch_id and clean(row.get("dimension_name")) in dimensions
        }
        first = next(iter(values.values()), {})
        status_values = [clean(row.get("parity_status", "")) for row in values.values()]
        if any(status.startswith("UNKNOWN") for status in status_values):
            status = "UNKNOWN_REQUIRES_REVIEW"
        elif any(status.startswith("WARN") for status in status_values):
            status = "WARN_REVIEW_VALUE_DIFFERENCE"
        else:
            status = "PASS"
        row: dict[str, Any] = {
            "batch_id": batch_id,
            "role": clean(first.get("role", "")),
            "parity_status": status,
            "notes": "; ".join(clean(item.get("parity_note", "")) for item in values.values() if clean(item.get("parity_note", ""))),
            "claim_boundary": CLAIM_BOUNDARY,
        }
        for dimension in dimensions:
            out_key = {
                "DEM mode": "dem_mode",
                "landcover mode": "landcover_mode",
                "forcing_day_id set": "forcing_day_id_set",
                "hour_sgt set": "hour_sgt_set",
                "scenarios": "scenarios",
                "tile extent / tile buffer / tile resolution": "tile_spec",
                "per-cell asset layout": "per_cell_asset_layout",
                "QGIS/UMEP algorithm id": "qgis_umep_algorithm_id",
                "SOLWEIG parameters": "solweig_parameters",
            }[dimension]
            row[out_key] = clean(values.get(dimension, {}).get("protocol_value", ""))
        rows.append(row)
    return rows


def run(config_path: str | Path = DEFAULT_CONFIG) -> list[dict[str, Any]]:
    """Run source lineage parity audit."""
    config = load_config(config_path)
    matrix = ensure_protocol_matrix(config, config_path)
    lineage_rows = build_lineage_rows(matrix)
    dsm_rows = build_dsm_rows(matrix)
    cdsm_rows = build_cdsm_rows(matrix)
    dem_lc_rows = build_dimension_pair_rows(matrix, ["DEM mode", "landcover mode"], DEM_LC_FIELDS)
    forcing_rows = build_dimension_pair_rows(matrix, ["forcing_day_id set", "hour_sgt set", "scenarios"], FORCING_FIELDS)
    tile_rows = build_dimension_pair_rows(matrix, ["tile extent / tile buffer / tile resolution", "per-cell asset layout"], TILE_FIELDS)
    param_rows = build_dimension_pair_rows(matrix, ["QGIS/UMEP algorithm id", "SOLWEIG parameters"], PARAM_FIELDS)

    write_csv_rows(out_path(config, "b87b3p_source_path_lineage_matrix.csv"), lineage_rows, LINEAGE_FIELDS)
    write_csv_rows(out_path(config, "b87b3p_dsm_version_parity.csv"), dsm_rows, DSM_FIELDS)
    write_csv_rows(out_path(config, "b87b3p_cdsm_version_parity.csv"), cdsm_rows, CDSM_FIELDS)
    write_csv_rows(out_path(config, "b87b3p_dem_landcover_parity.csv"), dem_lc_rows, DEM_LC_FIELDS)
    write_csv_rows(out_path(config, "b87b3p_forcing_design_parity.csv"), forcing_rows, FORCING_FIELDS)
    write_csv_rows(out_path(config, "b87b3p_tile_spec_parity.csv"), tile_rows, TILE_FIELDS)
    write_csv_rows(out_path(config, "b87b3p_solweig_parameter_parity.csv"), param_rows, PARAM_FIELDS)
    return lineage_rows


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Audit B8.7b.3p source/path lineage parity from compact protocol "
            "tables. No QGIS/SOLWEIG, raster pixel reads, svfs.zip opens, "
            "manifests/runners, staging, or commits."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    rows = run(args.config)
    print(f"source_lineage_rows={len(rows)}")


if __name__ == "__main__":
    main()
