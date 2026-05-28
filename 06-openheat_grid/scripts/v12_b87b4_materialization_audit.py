"""Audit local-only B87B4 materialized assets.

Inputs: config and local asset root.
Outputs: b87b4_materialized_asset_inventory.csv,
b87b4_materialized_asset_readiness_by_cell.csv,
b87b4_svf_materialization_status.csv, and b87b4_materialization_blocker_register.csv.
Saved metrics: per-asset existence, per-cell readiness, SVF readiness, and blockers.
"""

from __future__ import annotations

from pathlib import Path

from v12_b87b4_b87c_common import build_parser, run_named_step


if __name__ == "__main__":
    args = build_parser("Audit B87B4 local materialized assets.").parse_args()
    raise SystemExit(run_named_step("materialization_audit", Path(args.config)))
