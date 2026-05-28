"""Audit the B87C execution manifest.

Inputs: b87c_manifest.csv and config expectations.
Outputs: b87c_manifest_audit.csv.
Saved metrics: row count, cell/day/hour/scenario counts, not_ready rows, and
repo-heavy path reference checks.
"""

from __future__ import annotations

from pathlib import Path

from v12_b87b4_b87c_common import build_parser, run_named_step


if __name__ == "__main__":
    args = build_parser("Audit B87C manifest.").parse_args()
    raise SystemExit(run_named_step("manifest_audit", Path(args.config)))
