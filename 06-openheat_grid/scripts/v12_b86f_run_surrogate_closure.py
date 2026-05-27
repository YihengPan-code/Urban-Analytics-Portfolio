"""Run the full B8.6f surrogate closure mega-suite.

Inputs:
    configs/v12/systemb_b86f_surrogate_closure.yaml and all compact CSV inputs
    declared there.
Outputs:
    All B8.6f compact CSV/Markdown outputs under
    outputs/v12_surrogate/b8_6f_surrogate_closure/ plus the UTF-8 Chinese
    documentation file in docs/v12.
Saved metrics:
    Input inventory, B8.6e caveat register, failure synthesis, spatial
    decision table, anchor/neutral failure matrix, safe-feature probe verdict,
    N300 v1 audit, role quota plan, role-balanced N300 v2 candidate design,
    feature acquisition register/spec, abstention rule catalog and metrics,
    scope-limited surrogate metrics, AOI preflight readiness matrix, next-lane
    decision matrix, future Codex prompts, report, and lane status. No raster,
    QGIS, SOLWEIG, AOI-wide, B9, WBGT, hazard, risk, Tmrt-to-WBGT, observed
    truth, causal feature-importance, or System A/B coupling output is created.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from v12_b86f_abstention_gate import run as run_abstention_gate
from v12_b86f_failure_synthesis import run as run_failure_synthesis
from v12_b86f_feature_acquisition_plan import run as run_feature_acquisition_plan
from v12_b86f_input_inventory import DEFAULT_CONFIG, run as run_input_inventory
from v12_b86f_n300_design_review import run as run_n300_design_review
from v12_b86f_scope_limited_probe import run as run_scope_limited_probe
from v12_b86f_workflow_decision import run as run_workflow_decision


@dataclass(frozen=True)
class RunResult:
    """Full B8.6f run result."""

    status: str
    inputs_status: str
    n300_selected_rows: int
    aoi_preflight_status: str
    b9_status: str
    recommended_next_lane: str


def run(config_path: Path = DEFAULT_CONFIG) -> RunResult:
    """Run the complete B8.6f compact closure workflow."""
    inventory = run_input_inventory(config_path)
    print(inventory)
    if inventory.status == "B86F_BLOCKED_INPUT":
        return RunResult(
            status="B86F_BLOCKED_INPUT",
            inputs_status=inventory.status,
            n300_selected_rows=0,
            aoi_preflight_status="BLOCKED_INPUT",
            b9_status="BLOCKED",
            recommended_next_lane="fix compact input inventory",
        )
    failure = run_failure_synthesis(config_path)
    print(failure)
    n300 = run_n300_design_review(config_path)
    print(n300)
    feature = run_feature_acquisition_plan(config_path)
    print(feature)
    abstention = run_abstention_gate(config_path)
    print(abstention)
    scope = run_scope_limited_probe(config_path)
    print(scope)
    decision = run_workflow_decision(config_path)
    print(decision)
    return RunResult(
        status=decision.status,
        inputs_status=inventory.status,
        n300_selected_rows=n300.selected_rows,
        aoi_preflight_status=decision.aoi_preflight_status,
        b9_status=decision.b9_status,
        recommended_next_lane=decision.recommended_next_lane,
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Run the full B8.6f surrogate closure compact mega-suite.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
