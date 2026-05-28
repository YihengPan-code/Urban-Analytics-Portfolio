"""Build the real B87C execution manifest and companion package tables.

Inputs: candidate cells, forcing slots, local asset readiness, and config.
Outputs: b87c_manifest.csv plus batch/resume/instruction/postrun package tables.
Saved metrics: 3000-row run manifest, batch counts, resume strategy, and schema.
"""

from __future__ import annotations

from pathlib import Path

from v12_b87b4_b87c_common import build_parser, run_named_step


if __name__ == "__main__":
    args = build_parser("Build B87C manifest.").parse_args()
    raise SystemExit(run_named_step("manifest_builder", Path(args.config)))
