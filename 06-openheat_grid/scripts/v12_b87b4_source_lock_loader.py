"""Load B8.7b.3 source locks into the B8.7b.4/B87C package.

Inputs: b87b3 canonical source set and overhead inventory from config.
Outputs: b87b4_source_lock_summary.csv.
Saved metrics: lock status, current path existence, and B87B4 interpretation.
"""

from __future__ import annotations

from pathlib import Path

from v12_b87b4_b87c_common import build_parser, run_named_step


if __name__ == "__main__":
    args = build_parser("Load B87B3 source locks.").parse_args()
    raise SystemExit(run_named_step("source_lock_loader", Path(args.config)))
