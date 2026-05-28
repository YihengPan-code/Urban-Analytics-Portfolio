"""Create approved local-only B87C directories under C:/OpenHeat-local.

Inputs: local_root/local_asset_root/local_output_root/local_run_log_root from config.
Outputs: b87b4_local_root_setup.csv.
Saved metrics: directory creation/existence status and approved-root safety status.
"""

from __future__ import annotations

from pathlib import Path

from v12_b87b4_b87c_common import build_parser, run_named_step


if __name__ == "__main__":
    args = build_parser("Set up B87C local root directories.").parse_args()
    raise SystemExit(run_named_step("local_root_setup", Path(args.config)))
