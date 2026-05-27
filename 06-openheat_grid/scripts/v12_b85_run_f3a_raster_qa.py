"""Run the B8.5-F3a micro-batch raster content QA.

Inputs:
    configs/v12/systemb_b85_f3a_raster_qa.yaml
    B8.5-F3a micro-batch manifest and postrun validation CSV declared in the
    config, plus the four local `Tmrt_average.tif` raster paths declared by
    the manifest.

Outputs:
    Raster inventory, per-run Tmrt stats, pairwise overhead_as_canopy - base
    deltas, FD02 - FD01 contrasts, alignment QA, sanity checks, English report,
    Chinese UTF-8 note, and lane status Markdown under the configured paths.

Saved metrics:
    Decision status, raster count opened, alignment status, per-run p90 range,
    base-vs-overhead delta headline, FD02-vs-FD01 contrast headline, next
    recommended action, and generated file list.

This runner does not stage, commit, run QGIS, run SOLWEIG, copy/open svfs.zip,
create/copy/move rasters, write raster/image outputs, create AOI-wide
predictions, compute local WBGT, create hazard_score/risk_score, or create
System A/B coupling outputs.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from v12_b85_f3a_raster_qa import DEFAULT_CONFIG, FAILED, path_text, repo_path, run


def main() -> int:
    """Parse CLI args and run the B8.5-F3a raster QA."""
    parser = argparse.ArgumentParser(
        description=(
            "Create B8.5-F3a raster content QA artifacts by reading only the "
            "four local Tmrt_average.tif rasters declared in the manifest."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="B8.5-F3a raster QA YAML config path.")
    args = parser.parse_args()
    result = run(repo_path(args.config))
    print(f"Decision status: {result.decision_status}")
    print(f"Raster count opened: {result.raster_count_opened}")
    print(f"Alignment status: {result.alignment_status}")
    print(f"Per-run p90 range: {result.per_run_p90_range}")
    print(f"Base-vs-overhead delta headline: {result.pairwise_delta_headline}")
    print(f"FD02-vs-FD01 contrast headline: {result.forcing_day_contrast_headline}")
    print(f"Next recommended action: {result.next_recommended_action}")
    print("QGIS/SOLWEIG executed: no")
    print("Raster outputs written: no")
    print("Files created:")
    for path in result.files_created:
        print(f"- {path_text(path)}")
    return 0 if result.decision_status != FAILED else 1


if __name__ == "__main__":
    raise SystemExit(main())
