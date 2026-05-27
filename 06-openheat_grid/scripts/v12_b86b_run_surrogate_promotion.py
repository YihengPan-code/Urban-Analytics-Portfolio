"""Run the complete B8.6b surrogate promotion review.

Inputs:
    configs/v12/systemb_b86b_surrogate_promotion.yaml and all compact inputs
    declared in the config.

Outputs:
    All compact B8.6b CSV/Markdown outputs under
    outputs/v12_surrogate/b8_6b_surrogate_promotion/ plus
    docs/v12/OpenHeat_SystemB_B8_6b_surrogate_promotion_CN.md.

Saved metrics:
    Input inventories, F5 label/feature readiness, surrogate dataset and
    schemas, validation split manifest, sklearn model metrics, holdout
    summaries, target sensitivity, top-k overlaps, anchor/neutral/unstable
    diagnostics, worst-error inventory, non-causal feature diagnostics,
    promotion decision matrix, model card, report, CN doc, and lane status.

This runner does not run QGIS or SOLWEIG, does not read raster files, does
not open or copy svfs.zip, does not create AOI-wide prediction, does not
convert Tmrt to WBGT, and does not create WBGT, hazard_score, risk_score,
B9, or System A/B coupling outputs.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from v12_b86b_error_audit import run as run_audit
from v12_b86b_surrogate_dataset import run as run_dataset
from v12_b86b_surrogate_inventory import DEFAULT_CONFIG, repo_path, run as run_inventory
from v12_b86b_surrogate_models import run as run_models
from v12_b86b_validation_splits import run as run_splits


def run(config_path: Path = DEFAULT_CONFIG) -> dict[str, object]:
    """Run inventory, dataset, validation, models, and audit/report steps."""
    inventory = run_inventory(config_path)
    dataset = run_dataset(config_path)
    splits = run_splits(config_path)
    models = run_models(config_path)
    audit = run_audit(config_path)
    return {
        "inventory": asdict(inventory),
        "dataset": asdict(dataset),
        "validation_splits": asdict(splits),
        "models": asdict(models),
        "audit": asdict(audit),
    }


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Run B8.6b surrogate promotion review.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to B8.6b YAML config.")
    args = parser.parse_args()
    result = run(repo_path(args.config))
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
