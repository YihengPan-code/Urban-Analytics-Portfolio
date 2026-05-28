"""Plan local-only B87B4 materialization tasks.

Inputs: candidate cells, source locks, local roots, and scenario rules from config.
Outputs: b87b4_scenario_asset_plan.csv and b87b4_materialization_task_plan.csv.
Saved metrics: required asset paths, runtime ownership, and repo/local write policy.
"""

from __future__ import annotations

from pathlib import Path

from v12_b87b4_b87c_common import build_parser, run_named_step


if __name__ == "__main__":
    args = build_parser("Plan B87B4 local materialization tasks.").parse_args()
    raise SystemExit(run_named_step("materialization_plan", Path(args.config)))
