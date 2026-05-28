"""Run the full B8.6g3 true-vector source-review closeout suite.

Inputs:
    configs/v12/systemb_b86g3_true_vector_source_review.yaml and all compact
    inputs declared there.
Outputs:
    B8.6g3 input/source inventories, per-category true-vector source reviews,
    manual source-review closeout, N300 v4 source-reviewed design, v4 diff,
    execution-precheck readiness matrix, AOI/B9 blocker matrix, source-gap
    register, next-lane matrix, future Codex prompts, report, status, and
    Chinese documentation.
Saved metrics:
    Source-review cell closeout, v4 row count, N150 overlap, duplicate count,
    connected shade corridor verdict, pedestrian network verdict,
    building/canyon verdict, B8.7b precheck readiness, AOI/B9 blocker headline,
    and recommended next lane. This suite creates no SOLWEIG manifest, QGIS
    runner, local runner, raster, AOI-wide prediction, B9, local WBGT,
    hazard/risk/exposure/vulnerability score, observed-truth claim, causal
    feature-importance claim, Tmrt-to-WBGT conversion, or System A/B coupling.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from v12_b86g3_cell_source_closeout import run as run_cell_closeout
from v12_b86g3_execution_gate import run as run_execution_gate
from v12_b86g3_input_inventory import DEFAULT_CONFIG, InputInventoryResult
from v12_b86g3_input_inventory import run as run_input_inventory
from v12_b86g3_source_inventory import run as run_source_inventory
from v12_b86g3_vector_source_review import run as run_vector_source_review
from v12_b86g3_workflow_decision import WorkflowDecisionResult
from v12_b86g3_workflow_decision import run as run_workflow_decision


@dataclass(frozen=True)
class B86G3RunResult:
    """Full B8.6g3 run result."""

    status: str
    ready_for_b87b: bool
    needs_external_vector_source: bool
    recommended_next_lane: str


def blocked_result(inventory: InputInventoryResult) -> B86G3RunResult:
    """Return blocked-input run result."""
    return B86G3RunResult(
        status="B86G3_BLOCKED_INPUT",
        ready_for_b87b=False,
        needs_external_vector_source=False,
        recommended_next_lane=(
            "repair required inputs; "
            f"missing={inventory.missing_required_inputs}; schema_errors={inventory.schema_errors}"
        ),
    )


def run(config_path: Path = DEFAULT_CONFIG) -> B86G3RunResult:
    """Run the complete B8.6g3 source-review closeout suite."""
    inventory = run_input_inventory(config_path)
    print(inventory)
    if inventory.status == "B86G3_BLOCKED_INPUT":
        return blocked_result(inventory)
    source = run_source_inventory(config_path)
    print(source)
    vector = run_vector_source_review(config_path)
    print(vector)
    closeout = run_cell_closeout(config_path)
    print(closeout)
    gate = run_execution_gate(config_path)
    print(gate)
    decision: WorkflowDecisionResult = run_workflow_decision(config_path)
    print(decision)
    return B86G3RunResult(
        status=decision.status,
        ready_for_b87b=decision.ready_for_b87b,
        needs_external_vector_source=decision.needs_external_vector_source,
        recommended_next_lane=decision.recommended_next_lane,
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Run B8.6g3 true-vector source review and B8.7a source-review "
            "closeout. Creates compact review/design-gate outputs only; no "
            "raster/QGIS/SOLWEIG/manifest/AOI/B9/WBGT/hazard/risk output."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
