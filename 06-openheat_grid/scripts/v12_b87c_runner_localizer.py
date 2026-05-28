"""Copy B87B4/B87C QGIS runners and compact config/manifest to the local root.

Inputs: repo QGIS runner scripts, config, and b87c_manifest.csv.
Outputs: local runner/config/manifest copies under C:/OpenHeat-local and
b87c_local_runner_inventory.csv.
Saved metrics: local copy status and default RUN_ENABLED/DRY_RUN safety switches.
"""

from __future__ import annotations

from pathlib import Path

from v12_b87b4_b87c_common import build_parser, run_named_step


if __name__ == "__main__":
    args = build_parser("Localize B87C QGIS runners.").parse_args()
    raise SystemExit(run_named_step("runner_localizer", Path(args.config)))
