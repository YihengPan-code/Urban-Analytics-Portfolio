"""Run the B8.5-F2a local asset readiness and dry-run planning gate.

Inputs:
    configs/v12/systemb_b85_f2_asset_readiness.yaml
    B8.5-F0 run matrix and B8.5-F1 execution-package artifacts declared in
    the config.

Outputs:
    Asset-level readiness CSV, run-level readiness CSV, missing-asset CSV,
    local output-root safety CSV, dry-run simulation log, manual checklist,
    Chinese note, and status Markdown under the configured output paths.

Saved metrics:
    Final READY/PARTIAL/BLOCKED decision, ready run count, missing asset
    classes, local output-root status, and dry-run simulation status per run.

This runner does not stage, commit, run QGIS, run SOLWEIG, create rasters,
copy rasters, create AOI-wide predictions, compute local WBGT, create
hazard_score/risk_score, or create System A/B coupling outputs.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from v12_b85_f2_asset_readiness import DEFAULT_CONFIG, repo_path, run


def main() -> int:
    """Parse CLI args and run the B8.5-F2a readiness gate."""
    parser = argparse.ArgumentParser(
        description=(
            "Create B8.5-F2a local asset readiness and dry-run simulation "
            "artifacts without calling QGIS/SOLWEIG."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="B8.5-F2a YAML config path.")
    args = parser.parse_args()
    result = run(repo_path(args.config))
    print(f"Status: {result.decision_status}")
    print(f"Ready runs: {result.ready_run_count}/{result.total_run_count}")
    print(f"Missing asset summary: {result.missing_asset_summary}")
    print(f"Local output root status: {result.local_output_root_status}")
    print("QGIS/SOLWEIG executed: no")
    print(f"Next recommended action: {result.next_recommended_action}")
    print("Files created:")
    for path in result.files_created:
        print(f"- {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
