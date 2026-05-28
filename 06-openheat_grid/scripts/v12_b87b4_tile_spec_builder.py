"""Build the per-cell B87C tile specification table.

Inputs: B87B new-candidate index and tile convention values from config.
Outputs: b87b4_tile_spec_by_cell.csv.
Saved metrics: focus size, buffer, resolution, expected pixel dimensions, and local paths.
"""

from __future__ import annotations

from pathlib import Path

from v12_b87b4_b87c_common import build_parser, run_named_step


if __name__ == "__main__":
    args = build_parser("Build B87C tile specs.").parse_args()
    raise SystemExit(run_named_step("tile_spec_builder", Path(args.config)))
