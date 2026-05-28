"""Lock the B8.7b.3 canonical source versions.

Inputs:
    b87b3_manual_source_ingest.csv and canonical path fields from
    configs/v12/systemb_b87b3_full_raster_source_preplan.yaml.
Outputs:
    b87b3_version_lock_decision.csv, b87b3_canonical_source_set.csv,
    b87b3_not_applicable_source_register.csv, and
    b87b3_rejected_deprecated_source_register.csv.
Saved metrics:
    Canonical path, existence by metadata, lock status, version justification,
    rejected/deprecated source register, and not-applicable source register.
    No raster pixel values are read and no raster files are written, copied,
    moved, or symlinked.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from v12_b87b3_input_inventory import (
    CLAIM_BOUNDARY,
    DEFAULT_CONFIG,
    clean,
    config_list,
    load_config,
    metadata_for_path,
    out_path,
    path_exists_text,
    write_csv_rows,
)


def canonical_rows(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Return deterministic canonical source-lock rows."""
    dsm = clean(config["canonical_dsm_path"])
    cdsm = clean(config["canonical_cdsm_path"])
    grid = clean(config["canonical_grid_path"])
    base_svf = clean(config["canonical_base_svf_path"])
    rows = [
        {
            "source_kind": "dsm",
            "scenario": "all",
            "canonical_path": dsm,
            "user_decision": "use",
            "version_status": "qa_corrected_final",
            "lock_status": "LOCKED" if path_exists_text(dsm) == "yes" else "MISSING_CRITICAL_SOURCE",
            "required_for": "building obstruction geometry for base and overhead_as_canopy",
            "lock_reason": "Final building DSM after manual QA and height/geometry QA; supersedes v08 and intermediate v10 DSMs.",
        },
        {
            "source_kind": "cdsm_base_vegetation",
            "scenario": "base;overhead_as_canopy",
            "canonical_path": cdsm,
            "user_decision": "use",
            "version_status": "likely_final_base_vegetation_dsm",
            "lock_status": "LOCKED" if path_exists_text(cdsm) == "yes" else "MISSING_CRITICAL_SOURCE",
            "required_for": "existing vegetation DSM; overhead scenario combines max(existing vegetation DSM, overhead canopy)",
            "lock_reason": "Base 2 m vegetation DSM reused by v10/v12 flows.",
        },
        {
            "source_kind": "grid_geometry",
            "scenario": "all",
            "canonical_path": grid,
            "user_decision": "use",
            "version_status": "likely_final_geometry_source",
            "lock_status": "LOCKED" if path_exists_text(grid) == "yes" else "MISSING_CRITICAL_SOURCE",
            "required_for": "Toa Payoh 100 m cell geometry and N300 candidate coverage audit",
            "lock_reason": "Base Toa Payoh 100 m grid geometry with cell_id.",
        },
        {
            "source_kind": "svf_base_full",
            "scenario": "base",
            "canonical_path": base_svf,
            "user_decision": "use",
            "version_status": "likely_final_building_plus_existing_vegetation",
            "lock_status": "LOCKED_FULL_AOI_SOURCE_ONLY" if path_exists_text(base_svf) == "yes" else "MISSING_CRITICAL_SOURCE",
            "required_for": "base scenario SVF provenance and future per-tile SVF materialization",
            "lock_reason": "Full-AOI building + existing vegetation SVF; not per-tile SOLWEIG svfs.zip.",
        },
        {
            "source_kind": "svf_overhead",
            "scenario": "overhead_as_canopy",
            "canonical_path": "",
            "user_decision": "missing_or_to_generate",
            "version_status": "scenario_specific_materialization_required",
            "lock_status": "REQUIRES_SCENARIO_SPECIFIC_MATERIALIZATION",
            "required_for": "overhead_as_canopy scenario",
            "lock_reason": "Overhead scenario must not reuse base SVF; generate per-cell/tile SVF from building DSM + max(existing vegetation DSM, overhead canopy).",
        },
        {
            "source_kind": "dem",
            "scenario": "all",
            "canonical_path": "",
            "user_decision": "not_applicable_generate_flat_tile",
            "version_status": "flat_dem_convention",
            "lock_status": "NOT_APPLICABLE_GENERATE_FLAT_TILE",
            "required_for": "future SOLWEIG tile convention only",
            "lock_reason": "No canonical full DEM/DTM is required; later lane should generate flat DEM tiles locally.",
        },
        {
            "source_kind": "landcover",
            "scenario": "all",
            "canonical_path": "",
            "user_decision": "not_applicable_not_used",
            "version_status": "not_used_by_solweig_source_of_truth",
            "lock_status": "NOT_APPLICABLE_NOT_USED",
            "required_for": "not required",
            "lock_reason": "SOLWEIG source-of-truth uses INPUT_LC=None and USE_LC_BUILD=false.",
        },
    ]
    for row in rows:
        path = clean(row["canonical_path"])
        row["exists_by_metadata"] = path_exists_text(path)
        row["metadata_only"] = "true"
        row["claim_boundary"] = CLAIM_BOUNDARY
    return rows


def rejected_rows(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Return rejected/deprecated source rows."""
    dsm = clean(config["canonical_dsm_path"])
    rows: list[dict[str, Any]] = []
    for path in config_list(config, "deprecated_dsm_paths"):
        rows.append(
            {
                "source_kind": "dsm",
                "rejected_path_or_pattern": path,
                "exists_by_metadata": path_exists_text(path),
                "rejection_reason": "deprecated_or_intermediate_dsm_version",
                "superseded_by": dsm,
                "allowed_future_use": "provenance_only",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    rows.extend(
        [
            {
                "source_kind": "svf_pure_building",
                "rejected_path_or_pattern": "pure building SVF",
                "exists_by_metadata": "not_checked_pattern_only",
                "rejection_reason": "not final; base scenario requires building + existing vegetation SVF",
                "superseded_by": clean(config["canonical_base_svf_path"]),
                "allowed_future_use": "provenance_only",
                "claim_boundary": CLAIM_BOUNDARY,
            },
            {
                "source_kind": "svf_pure_vegetation",
                "rejected_path_or_pattern": "pure vegetation SVF",
                "exists_by_metadata": "not_checked_pattern_only",
                "rejection_reason": "invalid alone because it omits building obstruction",
                "superseded_by": clean(config["canonical_base_svf_path"]),
                "allowed_future_use": "provenance_only",
                "claim_boundary": CLAIM_BOUNDARY,
            },
            {
                "source_kind": "svf_intermediate_or_test",
                "rejected_path_or_pattern": "v08/intermediate/test/smoke/microbatch SVF",
                "exists_by_metadata": "not_checked_pattern_only",
                "rejection_reason": "reject unless provenance only; not final N300 source lock",
                "superseded_by": clean(config["canonical_base_svf_path"]),
                "allowed_future_use": "provenance_only",
                "claim_boundary": CLAIM_BOUNDARY,
            },
        ]
    )
    return rows


def run(config_path: Path = DEFAULT_CONFIG) -> list[dict[str, Any]]:
    """Run source version locking."""
    config = load_config(config_path)
    canonical = canonical_rows(config)
    write_csv_rows(
        out_path(config, "b87b3_version_lock_decision.csv"),
        canonical,
        [
            "source_kind",
            "scenario",
            "canonical_path",
            "user_decision",
            "version_status",
            "exists_by_metadata",
            "lock_status",
            "required_for",
            "lock_reason",
            "metadata_only",
            "claim_boundary",
        ],
    )
    write_csv_rows(
        out_path(config, "b87b3_canonical_source_set.csv"),
        [row for row in canonical if not clean(row["lock_status"]).startswith("NOT_APPLICABLE")],
        [
            "source_kind",
            "scenario",
            "canonical_path",
            "user_decision",
            "version_status",
            "exists_by_metadata",
            "lock_status",
            "required_for",
            "lock_reason",
            "metadata_only",
            "claim_boundary",
        ],
    )
    write_csv_rows(
        out_path(config, "b87b3_not_applicable_source_register.csv"),
        [row for row in canonical if clean(row["lock_status"]).startswith("NOT_APPLICABLE")],
        [
            "source_kind",
            "scenario",
            "canonical_path",
            "user_decision",
            "version_status",
            "exists_by_metadata",
            "lock_status",
            "required_for",
            "lock_reason",
            "metadata_only",
            "claim_boundary",
        ],
    )
    rejected = rejected_rows(config)
    write_csv_rows(
        out_path(config, "b87b3_rejected_deprecated_source_register.csv"),
        rejected,
        [
            "source_kind",
            "rejected_path_or_pattern",
            "exists_by_metadata",
            "rejection_reason",
            "superseded_by",
            "allowed_future_use",
            "claim_boundary",
        ],
    )
    return canonical


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Lock canonical B8.7b.3 source versions and write source registers; "
            "metadata only, no raster pixel reads or raster writes."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(f"version_lock_rows={len(run(args.config))}")


if __name__ == "__main__":
    main()
