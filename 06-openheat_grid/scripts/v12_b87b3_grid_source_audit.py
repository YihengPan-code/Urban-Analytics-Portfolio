"""Audit the canonical grid geometry source for N300 candidate support.

Inputs:
    canonical_grid_path, b87b_new_candidate_sample_index_path, and
    b86g3_n300_v4_design_path from the B8.7b.3 config.
Outputs:
    b87b3_grid_source_audit.csv.
Saved metrics:
    Grid path existence, GeoJSON feature count, cell_id property coverage,
    150-new-candidate coverage, design row count, and metadata-only status.
    This is vector/text inspection only; no raster pixels are read and no
    raster assets are written.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from v12_b87b3_input_inventory import (
    CLAIM_BOUNDARY,
    DEFAULT_CONFIG,
    clean,
    load_config,
    metadata_for_path,
    out_path,
    read_csv_rows,
    repo_path,
    write_csv_rows,
    yes_no,
)


def candidate_ids(config: dict[str, Any]) -> list[str]:
    """Load expected 150 candidate IDs from compact CSV."""
    return [clean(row.get("cell_id")) for row in read_csv_rows(config["b87b_new_candidate_sample_index_path"]) if clean(row.get("cell_id"))]


def inspect_geojson(path: str, candidates: set[str]) -> dict[str, Any]:
    """Inspect GeoJSON feature properties and candidate coverage."""
    resolved = repo_path(path)
    try:
        data = json.loads(resolved.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        return {
            "vector_inspection_status": "VECTOR_NOT_CHECKED",
            "feature_count": "",
            "unique_cell_id_count": "",
            "candidate_cell_id_coverage_count": "",
            "contains_all_150_new_candidates": "unknown",
            "missing_candidate_cell_ids": "",
            "crs": "",
            "inspection_error": clean(exc),
        }
    features = data.get("features", []) if isinstance(data, dict) else []
    cell_ids = {
        clean(feature.get("properties", {}).get("cell_id"))
        for feature in features
        if isinstance(feature, dict) and clean(feature.get("properties", {}).get("cell_id"))
    }
    missing = sorted(candidates - cell_ids)
    crs = ""
    if isinstance(data, dict) and isinstance(data.get("crs"), dict):
        crs = clean(data.get("crs", {}).get("properties", {}).get("name"))
    return {
        "vector_inspection_status": "VECTOR_OK",
        "feature_count": len(features),
        "unique_cell_id_count": len(cell_ids),
        "candidate_cell_id_coverage_count": len(candidates & cell_ids),
        "contains_all_150_new_candidates": yes_no(not missing),
        "missing_candidate_cell_ids": "|".join(missing),
        "crs": crs,
        "inspection_error": "",
    }


def run(config_path: Path = DEFAULT_CONFIG) -> list[dict[str, Any]]:
    """Run grid source audit."""
    config = load_config(config_path)
    path = clean(config["canonical_grid_path"])
    meta = metadata_for_path(path)
    candidates = set(candidate_ids(config))
    design_rows = read_csv_rows(config["b86g3_n300_v4_design_path"])
    inspected = inspect_geojson(path, candidates) if meta["exists_by_metadata"] == "yes" else {
        "vector_inspection_status": "VECTOR_NOT_CHECKED",
        "feature_count": "",
        "unique_cell_id_count": "",
        "candidate_cell_id_coverage_count": "",
        "contains_all_150_new_candidates": "no",
        "missing_candidate_cell_ids": "|".join(sorted(candidates)),
        "crs": "",
        "inspection_error": "grid path missing by metadata",
    }
    rows = [
        {
            "grid_source_kind": "grid_geometry",
            "grid_path": path,
            "exists_by_metadata": meta["exists_by_metadata"],
            "is_file": meta["is_file"],
            "candidate_count_expected": clean(config["expected_new_candidate_count"]),
            "candidate_count_observed": len(candidates),
            "b86g3_design_row_count": len(design_rows),
            "supports_150_new_n300_cells": inspected["contains_all_150_new_candidates"],
            "grid_status": "LOCKED_SUPPORTS_N300" if inspected["contains_all_150_new_candidates"] == "yes" else "GRID_REVIEW_REQUIRED",
            **inspected,
            "metadata_only": "true",
            "claim_boundary": CLAIM_BOUNDARY,
        }
    ]
    write_csv_rows(
        out_path(config, "b87b3_grid_source_audit.csv"),
        rows,
        [
            "grid_source_kind",
            "grid_path",
            "exists_by_metadata",
            "is_file",
            "candidate_count_expected",
            "candidate_count_observed",
            "b86g3_design_row_count",
            "supports_150_new_n300_cells",
            "grid_status",
            "vector_inspection_status",
            "feature_count",
            "unique_cell_id_count",
            "candidate_cell_id_coverage_count",
            "contains_all_150_new_candidates",
            "missing_candidate_cell_ids",
            "crs",
            "inspection_error",
            "metadata_only",
            "claim_boundary",
        ],
    )
    return rows


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Audit canonical grid geometry coverage for the 150 new N300 cells; "
            "vector/text inspection only, no raster IO."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(f"grid_audit_rows={len(run(args.config))}")


if __name__ == "__main__":
    main()
