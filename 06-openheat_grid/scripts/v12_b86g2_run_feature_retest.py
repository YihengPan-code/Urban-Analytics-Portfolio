"""Orchestrate the full B8.6g2 feature-upgraded surrogate retest.

Inputs:
    configs/v12/systemb_b86g2_feature_retest.yaml and all compact CSV inputs
    declared there.
Outputs:
    All B8.6g2 compact outputs under
    outputs/v12_surrogate/b8_6g2_feature_retest/ plus the UTF-8 Chinese
    documentation file in docs/v12.
Saved metrics:
    Input inventory, schema, leakage audit, feature registry, validation
    splits, single-stage metrics, two-stage metrics, ablation, diagnostics,
    baseline comparison, promotion gate, AOI readiness, next-lane decision,
    model card, report, and lane status.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from v12_b86g2_ablation import run as run_ablation
from v12_b86g2_dataset import run as run_dataset
from v12_b86g2_error_diagnostics import run as run_diagnostics
from v12_b86g2_feature_audit import run as run_feature_audit
from v12_b86g2_input_inventory import run as run_input_inventory
from v12_b86g2_single_stage_models import run as run_single_stage
from v12_b86g2_splits import run as run_splits
from v12_b86g2_two_stage_models import run as run_two_stage
from v12_b86g2_workflow_decision import run as run_decision
from v12_b86g2_common import DEFAULT_CONFIG


@dataclass(frozen=True)
class RunResult:
    """Full B8.6g2 runner result."""

    status: str
    recommended_next_lane: str
    selected_feature_set: str
    selected_classifier: str
    selected_regressor: str


def run(config_path: Path = DEFAULT_CONFIG) -> RunResult:
    """Run the complete compact B8.6g2 retest suite."""
    inventory = run_input_inventory(config_path)
    print(inventory)
    dataset = run_dataset(config_path)
    print(dataset)
    audit = run_feature_audit(config_path)
    print(audit)
    splits = run_splits(config_path)
    print(splits)
    single_stage = run_single_stage(config_path)
    print(single_stage)
    two_stage = run_two_stage(config_path)
    print(two_stage)
    ablation = run_ablation(config_path)
    print(ablation)
    diagnostics = run_diagnostics(config_path)
    print(diagnostics)
    decision = run_decision(config_path)
    print(decision)
    return RunResult(
        decision.status,
        decision.recommended_next_lane,
        decision.selected_feature_set,
        decision.selected_classifier,
        decision.selected_regressor,
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Run the full B8.6g2 feature-upgraded compact surrogate retest suite.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
