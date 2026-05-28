"""Write the B8.7b.3 SVF scenario model and SVF version audit.

Inputs:
    b87b3_version_lock_decision.csv and b87b3_overhead_source_inventory.csv.
Outputs:
    b87b3_svf_scenario_model.csv and b87b3_svf_candidate_version_audit.csv.
Saved metrics:
    Base and overhead_as_canopy SVF geometry definitions, full-AOI SVF source
    status, per-cell/tile svfs.zip materialization requirement, rejected SVF
    classes, and caveats. No SVF generation, QGIS/SOLWEIG execution, svfs.zip
    opening, or raster writing is performed.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from v12_b87b3_input_inventory import (
    CLAIM_BOUNDARY,
    DEFAULT_CONFIG,
    clean,
    load_config,
    out_path,
    path_exists_text,
    read_csv_rows,
    write_csv_rows,
)


def overhead_found(config: dict[str, Any]) -> str:
    """Return yes/no for recovered overhead vector availability."""
    try:
        rows = read_csv_rows(out_path(config, "b87b3_overhead_source_inventory.csv"))
    except FileNotFoundError:
        return "no"
    return "yes" if any(clean(row.get("supports_overhead_scenario")) == "yes" for row in rows) else "no"


def scenario_rows(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the explicit SVF scenario model rows."""
    base_svf = clean(config["canonical_base_svf_path"])
    overhead_ok = overhead_found(config)
    return [
        {
            "scenario_id": "base",
            "geometry_definition": "building DSM + existing vegetation DSM",
            "building_dsm_source": clean(config["canonical_dsm_path"]),
            "vegetation_or_canopy_source": clean(config["canonical_cdsm_path"]),
            "full_svf_source": base_svf,
            "full_svf_source_status": "LOCKED_FULL_AOI_SOURCE_ONLY" if path_exists_text(base_svf) == "yes" else "MISSING_CRITICAL_SOURCE",
            "materialization_required": "per-cell/tile svfs.zip or equivalent local SOLWEIG SVF input",
            "svf_reuse_rule": "base full-AOI SVF can inform only base scenario materialization; it is not a per-tile svfs.zip",
            "supports_future_materialization": "yes" if path_exists_text(base_svf) == "yes" else "no",
            "notes": "Base SVF includes buildings plus existing vegetation.",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "scenario_id": "overhead_as_canopy",
            "geometry_definition": "building DSM + max(existing vegetation DSM, overhead canopy)",
            "building_dsm_source": clean(config["canonical_dsm_path"]),
            "vegetation_or_canopy_source": clean(config["canonical_cdsm_path"]) + " + overhead_structures_v10.geojson",
            "full_svf_source": "missing_or_to_generate",
            "full_svf_source_status": "SCENARIO_SPECIFIC_SVF_REQUIRED",
            "materialization_required": "scenario-specific per-cell/tile svfs.zip",
            "svf_reuse_rule": "must not reuse base SVF",
            "supports_future_materialization": overhead_ok,
            "notes": "Future lane must generate overhead-aware SVF from the overhead canopy geometry.",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "scenario_id": "rejected",
            "geometry_definition": "pure building SVF; pure vegetation SVF; v08/intermediate/test/smoke/microbatch SVF",
            "building_dsm_source": "",
            "vegetation_or_canopy_source": "",
            "full_svf_source": "not_final_or_invalid",
            "full_svf_source_status": "REJECTED_EXCEPT_PROVENANCE_ONLY",
            "materialization_required": "not_applicable",
            "svf_reuse_rule": "do not use for final N300 labels",
            "supports_future_materialization": "no",
            "notes": "Pure building SVF omits existing vegetation; pure vegetation SVF omits buildings; old/test SVF is provenance only.",
            "claim_boundary": CLAIM_BOUNDARY,
        },
    ]


def audit_rows(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Return compact SVF candidate/version audit rows."""
    base_svf = clean(config["canonical_base_svf_path"])
    return [
        {
            "svf_candidate": "v10 umep_svf_with_veg/SkyViewFactor.tif",
            "scenario": "base",
            "candidate_path": base_svf,
            "exists_by_metadata": path_exists_text(base_svf),
            "version_status": "likely_final_base_full_aoi_svf",
            "decision": "use_as_base_full_AOI_source_only",
            "reason": "building + existing vegetation SVF recovered from v10 gamma UMEP source of truth",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "svf_candidate": "overhead_as_canopy SVF",
            "scenario": "overhead_as_canopy",
            "candidate_path": "",
            "exists_by_metadata": "not_applicable_to_generate",
            "version_status": "missing_or_to_generate",
            "decision": "generate_scenario_specific_per_tile_svf_later",
            "reason": "overhead scenario requires building + vegetation + overhead geometry; base SVF cannot be reused",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "svf_candidate": "pure building SVF",
            "scenario": "rejected",
            "candidate_path": "",
            "exists_by_metadata": "not_checked_pattern_only",
            "version_status": "not_final",
            "decision": "reject",
            "reason": "base scenario includes existing vegetation DSM",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "svf_candidate": "pure vegetation SVF",
            "scenario": "rejected",
            "candidate_path": "",
            "exists_by_metadata": "not_checked_pattern_only",
            "version_status": "invalid_alone",
            "decision": "reject",
            "reason": "omits building obstruction",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "svf_candidate": "v08/intermediate/test/smoke/microbatch SVF",
            "scenario": "rejected",
            "candidate_path": "",
            "exists_by_metadata": "not_checked_pattern_only",
            "version_status": "deprecated_or_diagnostic_only",
            "decision": "reject_unless_provenance",
            "reason": "not final source lock for N300 materialization",
            "claim_boundary": CLAIM_BOUNDARY,
        },
    ]


def run(config_path: Path = DEFAULT_CONFIG) -> list[dict[str, Any]]:
    """Run SVF scenario model generation."""
    config = load_config(config_path)
    scenarios = scenario_rows(config)
    write_csv_rows(
        out_path(config, "b87b3_svf_scenario_model.csv"),
        scenarios,
        [
            "scenario_id",
            "geometry_definition",
            "building_dsm_source",
            "vegetation_or_canopy_source",
            "full_svf_source",
            "full_svf_source_status",
            "materialization_required",
            "svf_reuse_rule",
            "supports_future_materialization",
            "notes",
            "claim_boundary",
        ],
    )
    audits = audit_rows(config)
    write_csv_rows(
        out_path(config, "b87b3_svf_candidate_version_audit.csv"),
        audits,
        [
            "svf_candidate",
            "scenario",
            "candidate_path",
            "exists_by_metadata",
            "version_status",
            "decision",
            "reason",
            "claim_boundary",
        ],
    )
    return scenarios


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Write the base vs overhead_as_canopy SVF scenario model and SVF "
            "candidate audit; preplan only, no QGIS/SOLWEIG or raster writes."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(f"svf_scenario_rows={len(run(args.config))}")


if __name__ == "__main__":
    main()
