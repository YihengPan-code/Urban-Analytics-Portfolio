"""Run the B8.5-F2c FD02 SOLWEIG met forcing recovery/generation lane.

Inputs:
    configs/v12/systemb_b85_f2c_fd02_met_forcing.yaml
    Existing FD01 v09 met forcing templates, FD02 S128 weather rows, and B8.5
    compact readiness artifacts declared in the config.

Outputs:
    Source inventory, template schema inventory, FD02 weather rows, generated
    local-only met forcing manifest, validation table, readiness projection,
    next remap roots YAML, Chinese note, and status Markdown.

Saved metrics:
    Decision status, generated/recovered file count, selected template source,
    selected weather source, projected ready run count, remaining blockers, and
    QGIS/SOLWEIG execution flag.

This runner does not stage, commit, run QGIS, run SOLWEIG, create/copy/open
rasters, copy/open svfs.zip, create AOI-wide predictions, compute local WBGT,
create hazard_score/risk_score, or create System A/B coupling outputs.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from v12_b85_f2c_fd02_met_forcing import DEFAULT_CONFIG, FAILED, path_text, repo_path, run


def main() -> int:
    """Parse CLI args and run the F2c workflow."""
    parser = argparse.ArgumentParser(
        description=(
            "Create B8.5-F2c FD02 local-only SOLWEIG met forcing text files "
            "and compact readiness artifacts without calling QGIS/SOLWEIG."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="B8.5-F2c YAML config path.")
    args = parser.parse_args()
    result = run(repo_path(args.config))
    print(f"Decision status: {result.decision_status}")
    print(f"Generated or recovered met forcing files: {result.generated_or_recovered_count}/5")
    print(f"Template source: {result.template_source or 'none'}")
    print(f"Weather source: {result.weather_source or 'none'}")
    print(f"Projected ready runs after FD02 met generation: {result.projected_ready_run_count}/480")
    print(f"Remaining blockers: {result.remaining_blockers}")
    print("QGIS/SOLWEIG executed: no")
    print("Files created:")
    for path in result.files_created:
        print(f"- {path_text(path)}")
    return 0 if result.decision_status != FAILED else 1


if __name__ == "__main__":
    raise SystemExit(main())
