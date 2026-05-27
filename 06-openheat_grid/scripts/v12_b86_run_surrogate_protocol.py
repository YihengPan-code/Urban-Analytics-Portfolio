"""Run the complete B8.6 System B surrogate protocol / baseline gate.

Inputs:
    configs/v12/systemb_b86_surrogate_protocol.yaml and all compact input
    paths declared in it.

Outputs:
    All B8.6 compact CSV/Markdown artifacts under
    outputs/v12_surrogate/b8_6_surrogate_protocol/ plus
    docs/v12/OpenHeat_SystemB_B8_6_surrogate_protocol_CN.md.

Saved metrics:
    Input inventories, selected label/feature sources, dataset and target
    schemas, validation split manifests, baseline model metrics, holdout
    summaries, target sensitivity, N24 stress-validation bridge, decision
    matrix, promotion gate, model-card draft, report, and status summary.

This runner does not run QGIS or SOLWEIG, does not read raster files, does not
copy svfs.zip, does not create an N150 execution runner or manifest, does not
create AOI-wide prediction, and does not create local WBGT, hazard_score,
risk_score, B9, or System A/B coupling outputs.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from v12_b86_surrogate_baseline import run as run_baseline
from v12_b86_surrogate_dataset import run as run_dataset
from v12_b86_surrogate_inventory import DEFAULT_CONFIG, repo_path, run as run_inventory


def run(config_path: Path = DEFAULT_CONFIG) -> dict[str, object]:
    """Run inventory, dataset/splits, and baseline/report steps."""
    inventory = run_inventory(config_path)
    dataset = run_dataset(config_path)
    baseline = run_baseline(config_path)
    return {
        "inventory": asdict(inventory),
        "dataset": asdict(dataset),
        "baseline": asdict(baseline),
    }


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Run B8.6 surrogate protocol / baseline gate.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to B8.6 YAML config.")
    args = parser.parse_args()
    result = run(repo_path(args.config))
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
