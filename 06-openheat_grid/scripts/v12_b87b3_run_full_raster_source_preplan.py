"""Run the complete B8.7b.3 source-lock and materialization-preplan pipeline.

Inputs:
    configs/v12/systemb_b87b3_full_raster_source_preplan.yaml and the compact
    prior/manual inputs declared there.
Outputs:
    All required B8.7b.3 CSV/Markdown artifacts under
    outputs/v12_surrogate/b8_7b3_full_raster_source_preplan plus the Chinese
    documentation note under docs/v12.
Saved metrics:
    Input inventory, manual source ingestion, canonical source version locks,
    SVF scenario model, overhead source inventory, header-only raster metadata,
    grid source audit, extraction feasibility, local-only materialization
    preplan, B87C readiness projection/blockers, no-raster audit, next-lane
    decision matrix, prompts, report, and status. This runner does not execute
    QGIS/SOLWEIG, read raster pixels, write/copy/move/symlink rasters, create
    per-cell raster assets, open svfs.zip, create a run-ready manifest/runner,
    stage, or commit.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from v12_b87b3_extraction_feasibility import run as run_extraction_feasibility
from v12_b87b3_grid_source_audit import run as run_grid_source_audit
from v12_b87b3_header_metadata import run as run_header_metadata
from v12_b87b3_input_inventory import DEFAULT_CONFIG, run as run_input_inventory
from v12_b87b3_manual_source_ingest import run as run_manual_source_ingest
from v12_b87b3_materialization_preplan import run as run_materialization_preplan
from v12_b87b3_overhead_source_locator import run as run_overhead_source_locator
from v12_b87b3_readiness_decision import ReadinessDecision, run as run_readiness_decision
from v12_b87b3_svf_scenario_model import run as run_svf_scenario_model
from v12_b87b3_version_lock import run as run_version_lock


def print_final_summary(decision: ReadinessDecision) -> None:
    """Print the required final lane summary."""
    print(f"1. {decision.status}")
    print(f"2. DSM canonical status: {decision.dsm_status}")
    print(f"3. CDSM canonical status: {decision.cdsm_status}")
    print(f"4. grid status: {decision.grid_status}")
    print(f"5. DEM/landcover not-applicable status: {decision.dem_landcover_status}")
    print(f"6. base SVF status: {decision.base_svf_status}")
    print(f"7. overhead SVF status: {decision.overhead_svf_status}")
    print(f"8. overhead source status: {decision.overhead_source_status}")
    print(f"9. header metadata status: {decision.header_metadata_status}")
    print(f"10. extraction/materialization feasibility headline: {decision.feasibility_headline}")
    print(f"11. no-raster-write/no-pixel-read audit headline: {decision.audit_headline}")
    print(f"12. next lane recommendation: {decision.next_lane}")
    print("13. files created:")
    for path in decision.files_created:
        print(f"    - {path}")
    print("14. git status --short -- .: see b87b3_report.md and final shell check")


def run(config_path: Path = DEFAULT_CONFIG) -> ReadinessDecision:
    """Run all B8.7b.3 steps in dependency order."""
    inventory = run_input_inventory(config_path)
    if inventory.status != "PASS":
        print(f"input_inventory_status={inventory.status}")
    print(f"manual_source_rows={len(run_manual_source_ingest(config_path))}")
    print(f"version_lock_rows={len(run_version_lock(config_path))}")
    print(f"overhead_source_rows={len(run_overhead_source_locator(config_path))}")
    print(f"svf_scenario_rows={len(run_svf_scenario_model(config_path))}")
    print(f"header_metadata_rows={len(run_header_metadata(config_path))}")
    print(f"grid_source_rows={len(run_grid_source_audit(config_path))}")
    print(f"extraction_feasibility_rows={len(run_extraction_feasibility(config_path))}")
    print(f"materialization_preplan_rows={len(run_materialization_preplan(config_path))}")
    decision = run_readiness_decision(config_path)
    print_final_summary(decision)
    return decision


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Run B8.7b.3 manual source ingestion, source lock, SVF scenario "
            "model, overhead locator, metadata/header audit, and preplan. "
            "No QGIS/SOLWEIG, no raster pixel reads, no raster writes, no "
            "manifest/runner."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    try:
        run(args.config)
    except Exception as exc:
        print("1. FAILED")
        print(f"error: {exc}")
        raise


if __name__ == "__main__":
    main()
