"""Run the B8.5-F2b local SOLWEIG asset recovery/remap gate.

Inputs:
    configs/v12/systemb_b85_f2b_asset_recovery_remap.yaml
    B8.5-F2a missing-asset and run-readiness artifacts, B8.5-F0 run matrix,
    and B8.5-F1 required asset inventory declared in the config.

Outputs:
    Root-candidate inventory, per-missing-asset recovery table, remap table,
    missing-after-remap table, run-readiness-after-remap table, readiness
    delta summary, local output-root plan, met-forcing recovery plan, manual
    checklist, Chinese note, and status Markdown.

Saved metrics:
    Final READY/PARTIAL/NO_ASSET/BLOCKED decision, F2a/F2b ready-run counts,
    recovered and still-missing counts by asset type, selected root aliases,
    local output-root action, and QGIS/SOLWEIG execution flag.

This runner does not stage, commit, run QGIS, run SOLWEIG, create rasters,
copy rasters, open rasters for analysis, copy/open svfs.zip, create AOI-wide
predictions, compute local WBGT, create hazard_score/risk_score, or create
System A/B coupling outputs.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from v12_b85_f2b_asset_recovery_remap import DEFAULT_CONFIG, path_text, repo_path, run, sorted_counter_text


def main() -> int:
    """Parse CLI args and run the B8.5-F2b remap gate."""
    parser = argparse.ArgumentParser(
        description=(
            "Create B8.5-F2b asset discovery and root-remap readiness artifacts "
            "without copying assets or calling QGIS/SOLWEIG."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="B8.5-F2b YAML config path.")
    args = parser.parse_args()
    result = run(repo_path(args.config))
    print(f"Decision status: {result.decision_status}")
    print(f"F2a ready runs: {result.f2a_ready_runs}/480")
    print(f"F2b ready runs strict: {result.f2b_ready_runs_strict}/480")
    print(f"F2b ready runs if output root created: {result.f2b_ready_runs_if_output_root_created}/480")
    print(f"F2b ready runs if QGIS check passes: {result.f2b_ready_runs_if_qgis_check_passes}/480")
    print(
        "F2b ready runs if output root created and QGIS check passes: "
        f"{result.f2b_ready_runs_if_both_pass}/480"
    )
    print(f"Recovered asset count by type: {sorted_counter_text(result.recovered_by_type) or 'none'}")
    print(f"Still missing asset count by type: {sorted_counter_text(result.still_missing_by_type) or 'none'}")
    print(f"Selected root aliases: {', '.join(result.selected_root_aliases) or 'none'}")
    print(f"Local output root action: {result.local_output_root_action}")
    print("QGIS/SOLWEIG executed: no")
    print("Files created:")
    for path in result.files_created:
        print(f"- {path_text(path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
