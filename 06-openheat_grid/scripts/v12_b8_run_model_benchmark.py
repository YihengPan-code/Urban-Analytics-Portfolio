"""Run the B8.2 System B surrogate model benchmark.

Inputs:
    configs/v12/systemb_surrogate_b8_model_benchmark.yaml
    Existing B8.0/B8.1 matrix, feature schema, and split manifests declared in
    the config.

Outputs:
    Compact benchmark artifacts under
    outputs/v12_surrogate/b8_model_benchmark/.

Saved metrics:
    Fold-level model metrics, out-of-fold predictions, top-k overlap,
    stratified errors, split-family summaries, a Markdown comparison report,
    and B8_2_BENCHMARK_STATUS.md.

This runner does not stage, commit, create AOI-wide prediction maps, compute
local WBGT, create hazard_score/risk_score, or couple System A and System B.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from v12_b8_prepare_surrogate_dataset import repo_path
from v12_b8_surrogate_model_benchmark import DEFAULT_CONFIG, run


def main() -> None:
    """Parse CLI args and run the benchmark."""
    parser = argparse.ArgumentParser(
        description=(
            "Run B8.2 baseline surrogate/emulator benchmarks for SOLWEIG-derived "
            "System B targets using existing B8.1 validation split manifests."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Benchmark YAML config path.")
    args = parser.parse_args()
    command = f"{Path(sys.executable).as_posix()} scripts/v12_b8_run_model_benchmark.py --config {args.config.as_posix()}"
    result = run(repo_path(args.config), commands=[command])
    print(f"Status: {result.status}")
    print(f"Feature count used: {result.feature_count}")
    print(f"Models completed: {', '.join(result.models_completed)}")
    print(f"Best model by cell_grouped MAE for delta_tmrt_p90_c: {result.best_cell_grouped_model}")
    print(f"Best model by spatial MAE for delta_tmrt_p90_c: {result.best_spatial_model}")
    print(f"Spearman / top-k headline: {result.spearman_topk_headline}")
    print(f"Benchmark report: {result.report_path}")
    print(f"Benchmark status: {result.status_path}")


if __name__ == "__main__":
    main()
