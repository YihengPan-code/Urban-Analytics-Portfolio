"""Run the full B8.7b.4/B87C local materialization package.

Inputs:
  --config configs/v12/systemb_b87b4_b87c_materialization_package.yaml

Outputs:
  - Required compact CSV/MD/Python outputs under
    outputs/v12_surrogate/b8_7b4_b87c_materialization_package/.
  - Local-only directories, focus-cell GeoJSONs, forcing files, local runner
    copies, and manifest copies under C:/OpenHeat-local/solweig/b87c_n300.

Saved metrics:
  Input inventory, source-lock summary, tile specs, scenario asset plans,
  materialization execution/audit, manifest/audit, batch/resume plans, runner
  inventory, postrun QA plan, git hygiene guard, readiness matrix, decision matrix,
  status, and final report.

This package does not run QGIS/SOLWEIG from Codex and does not write rasters,
svfs.zip, AOI/B9, WBGT, risk, or hazard outputs into Git.
"""

from __future__ import annotations

from pathlib import Path

from v12_b87b4_b87c_common import build_parser, load_config, run_package


if __name__ == "__main__":
    args = build_parser("Run the B87B4/B87C materialization package.").parse_args()
    status = run_package(load_config(Path(args.config)))
    print(status)
