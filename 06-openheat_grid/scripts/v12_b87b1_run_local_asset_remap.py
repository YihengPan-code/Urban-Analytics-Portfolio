"""Run the full B8.7b.1 local asset-remap readiness package.

Inputs:
    configs/v12/systemb_b87b1_local_asset_remap.yaml and the compact B8.7b,
    B8.6g3, and B8.5-F1/F2/F3/F5 inputs declared there.
Outputs:
    B8.7b.1 input inventory, prior local-root inventory, manual local-root
    template/instructions, asset pattern registry, per-cell expected paths,
    metadata audit, resolved readiness table, missing/root/blocker registers,
    B8.7c prerequisite checklist, no-raster-touch audit, next-lane matrix,
    future prompts, report, status, and Chinese documentation.
Saved metrics:
    Final PASS/READY/WAITING/PARTIAL/BLOCKED/DIAGNOSTIC/FAILED decision,
    manual-root presence, root resolution count, 150-cell readiness counts,
    per-asset ready counts, met forcing/output-root readiness, no-raster audit,
    AOI/B9 blocked status, and recommended next lane. This suite is local asset
    readiness only: no raster IO, no QGIS/SOLWEIG, no run-ready manifest, no
    QGIS/local runner, no local execution package, no AOI/B9 output, no local
    WBGT, no hazard/risk score, no Tmrt-to-WBGT conversion, and no System A/B
    coupling.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from v12_b87b1_asset_metadata_audit import run as run_asset_metadata_audit
from v12_b87b1_asset_path_patterns import run as run_asset_path_patterns
from v12_b87b1_cell_asset_resolver import run as run_cell_asset_resolver
from v12_b87b1_input_inventory import DEFAULT_CONFIG, InputInventoryResult
from v12_b87b1_input_inventory import run as run_input_inventory
from v12_b87b1_local_root_inventory import run as run_local_root_inventory
from v12_b87b1_manual_root_template import run as run_manual_root_template
from v12_b87b1_readiness_decision import ReadinessDecisionResult
from v12_b87b1_readiness_decision import run as run_readiness_decision


@dataclass(frozen=True)
class B87B1RunResult:
    """Full B8.7b.1 run result."""

    status: str
    manual_local_roots_found: bool
    roots_resolved_count: int
    new_candidate_count: int
    cell_tile_folder_resolved_count: int
    svf_ready_count: int
    dsm_ready_count: int
    cdsm_ready_count: int
    dem_ready_count: int
    landcover_ready_count: int
    met_forcing_ready_count: int
    output_root_ready_count: int
    missing_ambiguous_headline: str
    no_raster_touch_headline: str
    aoi_b9_status: str
    recommended_next_lane: str


def failed_result(inventory: InputInventoryResult) -> B87B1RunResult:
    """Return a failed result when required compact inputs are missing."""
    return B87B1RunResult(
        status="FAILED",
        manual_local_roots_found=inventory.manual_local_root_input_found,
        roots_resolved_count=0,
        new_candidate_count=0,
        cell_tile_folder_resolved_count=0,
        svf_ready_count=0,
        dsm_ready_count=0,
        cdsm_ready_count=0,
        dem_ready_count=0,
        landcover_ready_count=0,
        met_forcing_ready_count=0,
        output_root_ready_count=0,
        missing_ambiguous_headline=(
            f"missing_required={inventory.missing_required_inputs}; schema_errors={inventory.schema_errors}"
        ),
        no_raster_touch_headline="not evaluated after input failure",
        aoi_b9_status="AOI_PREFLIGHT_BLOCKED / B9_BLOCKED",
        recommended_next_lane="repair B8.7b.1 compact inputs",
    )


def from_decision(decision: ReadinessDecisionResult) -> B87B1RunResult:
    """Convert final decision to suite-level result."""
    return B87B1RunResult(
        status=decision.status,
        manual_local_roots_found=decision.manual_local_roots_found,
        roots_resolved_count=decision.roots_resolved_count,
        new_candidate_count=decision.new_candidate_count,
        cell_tile_folder_resolved_count=decision.cell_tile_folder_resolved_count,
        svf_ready_count=decision.svf_ready_count,
        dsm_ready_count=decision.dsm_ready_count,
        cdsm_ready_count=decision.cdsm_ready_count,
        dem_ready_count=decision.dem_ready_count,
        landcover_ready_count=decision.landcover_ready_count,
        met_forcing_ready_count=decision.met_forcing_ready_count,
        output_root_ready_count=decision.output_root_ready_count,
        missing_ambiguous_headline=decision.missing_ambiguous_headline,
        no_raster_touch_headline=decision.no_raster_touch_headline,
        aoi_b9_status="AOI_PREFLIGHT_BLOCKED / B9_BLOCKED",
        recommended_next_lane=decision.recommended_next_lane,
    )


def run(config_path: Path = DEFAULT_CONFIG) -> B87B1RunResult:
    """Run the complete B8.7b.1 local asset-remap readiness suite."""
    inventory = run_input_inventory(config_path)
    print(inventory)
    if inventory.status == "FAIL":
        return failed_result(inventory)
    roots = run_local_root_inventory(config_path)
    print(roots)
    manual = run_manual_root_template(config_path)
    print(manual)
    patterns = run_asset_path_patterns(config_path)
    print(patterns)
    resolver = run_cell_asset_resolver(config_path)
    print(resolver)
    audit = run_asset_metadata_audit(config_path)
    print(audit)
    decision = run_readiness_decision(config_path)
    print(decision)
    return from_decision(decision)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Run B8.7b.1 local asset remap readiness. Metadata only: no raster "
            "read/write/copy/open, no QGIS/SOLWEIG, no manifest, no runner."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
