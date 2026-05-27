"""Run the B8.5-F2d final readiness rerun.

Inputs:
    configs/v12/systemb_b85_f2d_readiness_final.yaml
    B8.5-F0 run matrix, B8.5-F2b asset remap table, B8.5-F2c next remap
    roots YAML, local output-root path, and optional QGIS manual check file
    declared in the config.

Outputs:
    Root inventory, asset status, 480-row run readiness table, readiness
    summary, execution precheck checklist, Chinese note, and status Markdown.

Saved metrics:
    Decision status, file-assets-ready count, ready-for-manual-QGIS count,
    output-root status, QGIS manual check status, remaining blockers, and
    QGIS/SOLWEIG execution flag.

This runner does not stage, commit, run QGIS, run SOLWEIG, create/copy/open
rasters, copy/open svfs.zip, create AOI-wide predictions, compute local WBGT,
create hazard_score/risk_score, or create System A/B coupling outputs.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from v12_b85_f2d_readiness_final import DEFAULT_CONFIG, FAILED, path_text, repo_path, run


def main() -> int:
    """Parse CLI args and run the F2d readiness rerun."""
    parser = argparse.ArgumentParser(
        description=(
            "Create B8.5-F2d final readiness artifacts without calling "
            "QGIS/SOLWEIG or opening/copying raster/SVF assets."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="B8.5-F2d YAML config path.")
    args = parser.parse_args()
    result = run(repo_path(args.config))
    print(f"Decision status: {result.decision_status}")
    print(f"File assets ready: {result.file_assets_ready_count}/480")
    print(f"Ready for manual QGIS: {result.ready_for_manual_qgis_count}/480")
    print(f"Output root status: {result.output_root_status}")
    print(f"QGIS manual check status: {result.qgis_manual_check_status}")
    print(f"Remaining blockers: {result.remaining_blockers}")
    print("QGIS/SOLWEIG executed: no")
    print("Files created:")
    for path in result.files_created:
        print(f"- {path_text(path)}")
    return 0 if result.decision_status != FAILED else 1


if __name__ == "__main__":
    raise SystemExit(main())
