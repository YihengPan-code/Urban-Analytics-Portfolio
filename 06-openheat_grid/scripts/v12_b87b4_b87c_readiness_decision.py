"""Write the B87B4/B87C readiness decision matrices and status docs.

Inputs: materialization audit, manifest, and runner inventory outputs.
Outputs: b87c_readiness_matrix.csv, b87c_next_lane_decision_matrix.csv,
B8_7B4_B87C_STATUS.md, and b87b4_b87c_report.md.
Saved metrics: source-lock headline, asset readiness counts, SVF readiness, manifest
row count, runner/localizer status, and AOI/B9 blocks.
"""

from __future__ import annotations

from pathlib import Path

from v12_b87b4_b87c_common import build_parser, run_named_step


if __name__ == "__main__":
    args = build_parser("Write B87B4/B87C readiness decision.").parse_args()
    raise SystemExit(run_named_step("readiness_decision", Path(args.config)))
