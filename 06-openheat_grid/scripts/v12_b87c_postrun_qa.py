"""Run compact B87C postrun QA after local QGIS execution.

Inputs: b87c_manifest.csv and local run logs under C:/OpenHeat-local.
Outputs: b87c_postrun_qa_summary.csv.
Saved metrics: manifest rows, missing Tmrt outputs, run-log status counts, and
git hygiene reminder. This script does not copy rasters or svfs.zip into Git.
"""

from __future__ import annotations

from pathlib import Path

from v12_b87b4_b87c_common import build_parser, run_named_step


if __name__ == "__main__":
    args = build_parser("Run B87C postrun QA.").parse_args()
    raise SystemExit(run_named_step("postrun_qa", Path(args.config)))
