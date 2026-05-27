"""Run the complete B8.6c feature hardening and failure audit suite.

Inputs:
    configs/v12/systemb_b86c_feature_hardening.yaml and all compact inputs
    declared in the config.

Outputs:
    All compact B8.6c CSV/Markdown outputs under
    outputs/v12_surrogate/b8_6c_feature_hardening/ plus
    docs/v12/OpenHeat_SystemB_B8_6c_feature_hardening_CN.md.

Saved metrics:
    Compact input inventory, feature safe/rejected catalogs, feature group and
    feature set registries, hardened F5 surrogate dataset, feature-set model
    metrics, OOF prediction audit, spatial/typology/anchor/neutral/unstable/h10
    failure audits, two-stage pretest metrics, surrogate workflow v0.1,
    B8.6d recommendation, decision matrix, report, status, and UTF-8 Chinese doc.

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

from v12_b86c_dataset import run as run_dataset
from v12_b86c_failure_audit import run as run_failure_audit
from v12_b86c_feature_inventory import DEFAULT_CONFIG, repo_path, run as run_inventory
from v12_b86c_feature_set_models import run as run_feature_set_models
from v12_b86c_two_stage_pretest import run as run_two_stage_pretest
from v12_b86c_workflow_spec import run as run_workflow_spec


def run(config_path: Path = DEFAULT_CONFIG) -> dict[str, object]:
    """Run inventory, dataset, model, failure, two-stage, and report steps."""
    inventory = run_inventory(config_path)
    dataset = run_dataset(config_path)
    feature_set_models = run_feature_set_models(config_path)
    failure_audit = run_failure_audit(config_path)
    two_stage = run_two_stage_pretest(config_path)
    workflow = run_workflow_spec(config_path)
    return {
        "inventory": asdict(inventory),
        "dataset": asdict(dataset),
        "feature_set_models": asdict(feature_set_models),
        "failure_audit": asdict(failure_audit),
        "two_stage_pretest": asdict(two_stage),
        "workflow": asdict(workflow),
    }


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Run the complete B8.6c feature hardening and failure audit suite.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to B8.6c YAML config.")
    args = parser.parse_args()
    result = run(repo_path(args.config))
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
