"""Summarize B8.6d neutral-threshold trade-offs.

Inputs:
    - b86d_combined_pipeline_metrics.csv
Outputs:
    - b86d_threshold_sweep_metrics.csv
Saved metrics:
    Neutral accuracy, false promotion, false neutral, Spearman, top10pct
    overlap, anchor MAE, spatial Spearman, and typology Spearman by threshold,
    feature set, classifier, and regressor.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from v12_b86d_common import DEFAULT_CONFIG, load_config, output_path, read_csv, write_csv
from v12_b86d_two_stage_pipeline import threshold_sweep


@dataclass(frozen=True)
class ThresholdSweepResult:
    """Threshold sweep result."""

    status: str
    rows: int


def run(config_path: Path = DEFAULT_CONFIG) -> ThresholdSweepResult:
    """Read combined metrics and write threshold sweep summary."""
    config = load_config(config_path)
    metrics = read_csv(output_path(config, "combined_pipeline_metrics"))
    sweep = threshold_sweep(metrics)
    write_csv(sweep, output_path(config, "threshold_sweep_metrics"))
    return ThresholdSweepResult("B86D_THRESHOLD_SWEEP_READY", len(sweep))


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Summarize B8.6d threshold sweep metrics.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
