"""Run the full B8.7b System B N300 execution-precheck suite.

Inputs:
    configs/v12/systemb_b87b_n300_execution_precheck.yaml and all compact
    inputs declared there.
Outputs:
    B8.7b input inventory, design validation, N300 sample indexes, forcing
    audit, expected run count, asset readiness, path remap audit, schema/run
    previews, batch/resume/failure strategy, runtime/storage estimate, Git
    hygiene guard, readiness decision, blocker and AOI/B9 matrices, future
    prompts, report, status, and Chinese documentation.
Saved metrics:
    Candidate count, existing N150 count, total unique cell count, expected
    additional run count, forcing design headline, local asset/path-remap
    readiness, pre-manifest/run-plan preview status, AOI/B9 blocked status, and
    recommended next lane. This suite is precheck-only: no QGIS, no SOLWEIG, no
    raster IO, no run-ready manifest, no QGIS/local runner, no AOI/B9 output,
    no local WBGT, no hazard/risk score, no Tmrt-to-WBGT conversion, and no
    System A/B coupling.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from v12_b87b_asset_readiness import run as run_asset_readiness
from v12_b87b_design_validation import run as run_design_validation
from v12_b87b_forcing_plan import run as run_forcing_plan
from v12_b87b_git_hygiene import run as run_git_hygiene
from v12_b87b_input_inventory import DEFAULT_CONFIG, InputInventoryResult
from v12_b87b_input_inventory import run as run_input_inventory
from v12_b87b_path_remap_audit import run as run_path_remap
from v12_b87b_precheck_decision import PrecheckDecisionResult
from v12_b87b_precheck_decision import run as run_precheck_decision
from v12_b87b_run_plan_preview import run as run_plan_preview
from v12_b87b_runtime_storage_estimate import run as run_runtime_storage
from v12_b87b_sample_index import run as run_sample_index


@dataclass(frozen=True)
class B87BRunResult:
    """Full B8.7b run result."""

    status: str
    n300_v4_candidate_count: int
    existing_n150_count: int
    total_unique_cell_count: int
    expected_additional_run_count: int
    forcing_headline: str
    asset_headline: str
    path_remap_headline: str
    recommended_next_lane: str


def failed_input_result(inventory: InputInventoryResult) -> B87BRunResult:
    """Return a failed result when required inputs or schemas block execution."""
    return B87BRunResult(
        status="FAILED",
        n300_v4_candidate_count=0,
        existing_n150_count=0,
        total_unique_cell_count=0,
        expected_additional_run_count=0,
        forcing_headline="input inventory failed",
        asset_headline=f"missing_required={inventory.missing_required_inputs}; schema_errors={inventory.schema_errors}",
        path_remap_headline="not evaluated",
        recommended_next_lane="repair required B8.7b inputs and rerun precheck",
    )


def run(config_path: Path = DEFAULT_CONFIG) -> B87BRunResult:
    """Run the complete B8.7b execution-precheck suite."""
    inventory = run_input_inventory(config_path)
    print(inventory)
    if inventory.status == "FAIL":
        return failed_input_result(inventory)
    design = run_design_validation(config_path)
    print(design)
    sample = run_sample_index(config_path)
    print(sample)
    forcing = run_forcing_plan(config_path)
    print(forcing)
    asset = run_asset_readiness(config_path)
    print(asset)
    remap = run_path_remap(config_path)
    print(remap)
    preview = run_plan_preview(config_path)
    print(preview)
    runtime = run_runtime_storage(config_path)
    print(runtime)
    hygiene = run_git_hygiene(config_path)
    print(hygiene)
    decision: PrecheckDecisionResult = run_precheck_decision(config_path)
    print(decision)
    return B87BRunResult(
        status=decision.status,
        n300_v4_candidate_count=decision.n300_v4_candidate_count,
        existing_n150_count=decision.existing_n150_count,
        total_unique_cell_count=decision.total_unique_cell_count,
        expected_additional_run_count=decision.expected_additional_run_count,
        forcing_headline=decision.forcing_headline,
        asset_headline=decision.asset_headline,
        path_remap_headline=decision.path_remap_headline,
        recommended_next_lane=decision.recommended_next_lane,
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Run the full B8.7b N300 execution-precheck suite. Precheck only: "
            "no raster IO, no QGIS/SOLWEIG, no run-ready manifest, no runner."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
