"""Run the B8.5-F0 System B multi-forcing preflight generator.

Inputs:
    configs/v12/systemb_b85_multiforcing_preflight.yaml
    Existing B8.3 model-card artifacts, B6/B7 N24/N150 label artifacts, and
    available System A/archive weather forcing tables declared in the config.

Outputs:
    Protocol, manifest, selected forcing-day inventory, N24 cell set,
    expected-output contract, QGIS handoff README, Chinese note, and status file
    under docs/v12 and outputs/v12_surrogate/b8_5_multiforcing_preflight/.

Saved metrics:
    N24 cell count/provenance, selected forcing-day summaries, planned run
    matrix row count, and protocol status.

This runner does not stage, commit, run QGIS, run SOLWEIG, create rasters,
create AOI-wide predictions, compute local WBGT, create hazard_score/risk_score,
or create System A/B coupling outputs.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from v12_b85_multiforcing_preflight import DEFAULT_CONFIG, repo_path, run


def main() -> None:
    """Parse CLI args and run the B8.5-F0 preflight."""
    parser = argparse.ArgumentParser(
        description=(
            "Create the B8.5-F0 System B multi-forcing preflight protocol and "
            "planned N24 x forcing-day SOLWEIG run matrix. No QGIS/SOLWEIG "
            "execution is performed."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="B8.5-F0 YAML config path.")
    args = parser.parse_args()
    command = f"{Path(sys.executable).as_posix()} scripts/v12_b85_run_multiforcing_preflight.py --config {args.config.as_posix()}"
    result = run(repo_path(args.config), commands=[command])
    print(f"Status: {result.status}")
    print(f"N cells: {result.n_cells}")
    print(f"Selected forcing days: {', '.join(result.selected_forcing_days)}")
    print(f"Run matrix rows: {result.run_matrix_rows}")
    print(f"QGIS/SOLWEIG executed: {result.qgis_solweig_executed}")
    print(f"Next recommended action: {result.next_recommended_action}")
    print("Files created:")
    for path in result.files_created:
        print(f"- {path}")
    print(f"Status file: {result.status_path}")


if __name__ == "__main__":
    main()
