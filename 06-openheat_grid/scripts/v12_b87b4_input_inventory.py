"""Build the B8.7b.4/B87C input inventory.

Inputs: config path plus B8.7b.3/B8.7b precheck paths declared there.
Outputs: b87b4_input_inventory.csv.
Saved metrics: path existence and optional Python geospatial dependency status.
"""

from __future__ import annotations

from pathlib import Path

from v12_b87b4_b87c_common import build_parser, run_named_step


if __name__ == "__main__":
    args = build_parser("Build B87B4/B87C input inventory.").parse_args()
    raise SystemExit(run_named_step("input_inventory", Path(args.config)))
