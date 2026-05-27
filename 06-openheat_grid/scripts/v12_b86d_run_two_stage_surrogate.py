"""Orchestrate the full B8.6d compact two-stage surrogate validation suite.

Inputs:
    configs/v12/systemb_b86d_two_stage_surrogate.yaml and all compact CSV
    inputs declared there.
Outputs:
    All B8.6d compact outputs under
    outputs/v12_surrogate/b8_6d_two_stage_surrogate/ plus the UTF-8 Chinese
    documentation file in docs/v12.
Saved metrics:
    Dataset inventory/schema, validation splits, stage-1 classifier metrics,
    stage-2 regressor metrics, combined pipeline metrics, threshold sweep,
    seed stability, target role decision, diagnostics, promotion gate, model
    card, workflow spec, report, and lane status.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from v12_b86d_dataset import run as run_dataset
from v12_b86d_error_diagnostics import run as run_diagnostics
from v12_b86d_seed_stability import run as run_seed_stability
from v12_b86d_splits import run as run_splits
from v12_b86d_threshold_sweep import run as run_threshold_sweep
from v12_b86d_two_stage_pipeline import run as run_pipeline
from v12_b86d_workflow_report import run as run_report
from v12_b86d_common import DEFAULT_CONFIG


@dataclass(frozen=True)
class RunResult:
    """Full runner result."""

    status: str
    best_threshold: float
    best_classifier: str
    best_regressor: str


def run(config_path: Path = DEFAULT_CONFIG) -> RunResult:
    """Run the complete B8.6d compact validation workflow."""
    dataset_result = run_dataset(config_path)
    print(dataset_result)
    split_result = run_splits(config_path)
    print(split_result)
    pipeline_result = run_pipeline(config_path)
    print(pipeline_result)
    sweep_result = run_threshold_sweep(config_path)
    print(sweep_result)
    seed_result = run_seed_stability(config_path)
    print(seed_result)
    diagnostic_result = run_diagnostics(config_path)
    print(diagnostic_result)
    report_result = run_report(config_path)
    print(report_result)
    return RunResult(
        status=report_result.status,
        best_threshold=report_result.best_threshold,
        best_classifier=report_result.best_classifier,
        best_regressor=report_result.best_regressor,
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Run the full B8.6d two-stage surrogate validation suite.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
