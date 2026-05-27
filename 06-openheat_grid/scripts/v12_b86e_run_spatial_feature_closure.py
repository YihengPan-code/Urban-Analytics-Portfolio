"""Run the full B8.6e spatial failure / feature-gap closure suite.

Inputs:
    configs/v12/systemb_b86e_spatial_feature_closure.yaml and all compact CSV
    inputs declared there.
Outputs:
    All B8.6e compact CSV/Markdown outputs under
    outputs/v12_surrogate/b8_6e_spatial_feature_closure/ plus the UTF-8 Chinese
    documentation file in docs/v12.
Saved metrics:
    Input inventory, joined OOF failure dataset, spatial/typology/anchor/neutral
    audits, feature distribution shift, feature coverage and gap register,
    domain distance diagnostics, safe engineered features, diagnostic closure
    probe metrics, targeted N300 candidate design, decision matrix, report, and
    status. No raster, QGIS, SOLWEIG, AOI-wide, B9, WBGT, hazard, risk, or
    System A/B coupling operation is performed.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from v12_b86e_engineered_features import run as run_engineered_features
from v12_b86e_failure_join import run as run_failure_join
from v12_b86e_feature_gap_audit import run as run_feature_gap_audit
from v12_b86e_input_inventory import DEFAULT_CONFIG, run as run_input_inventory
from v12_b86e_spatial_closure_probe import run as run_spatial_closure_probe
from v12_b86e_spatial_domain_audit import run as run_spatial_domain_audit
from v12_b86e_targeted_sampling import run as run_targeted_sampling
from v12_b86e_workflow_decision import run as run_workflow_decision


@dataclass(frozen=True)
class RunResult:
    """Full B8.6e run result."""

    status: str
    dataset_rows: int
    dataset_cells: int
    targeted_candidates: int


def run(config_path: Path = DEFAULT_CONFIG) -> RunResult:
    """Run the complete B8.6e compact closure workflow."""
    inventory = run_input_inventory(config_path)
    print(inventory)
    if inventory.status == "B86E_BLOCKED_INPUT":
        return RunResult(status="B86E_BLOCKED_INPUT", dataset_rows=0, dataset_cells=0, targeted_candidates=0)
    failure_join = run_failure_join(config_path)
    print(failure_join)
    spatial_audit = run_spatial_domain_audit(config_path)
    print(spatial_audit)
    feature_gap = run_feature_gap_audit(config_path)
    print(feature_gap)
    engineered = run_engineered_features(config_path)
    print(engineered)
    probe = run_spatial_closure_probe(config_path)
    print(probe)
    targeted = run_targeted_sampling(config_path)
    print(targeted)
    decision = run_workflow_decision(config_path)
    print(decision)
    return RunResult(
        status=decision.status,
        dataset_rows=decision.dataset_rows,
        dataset_cells=decision.dataset_cells,
        targeted_candidates=decision.targeted_candidates,
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Run the full B8.6e spatial feature-closure compact suite.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
