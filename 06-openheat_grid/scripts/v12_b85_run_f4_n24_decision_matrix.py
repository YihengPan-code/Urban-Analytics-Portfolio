"""Run the B8.5-F4 N24 stability decision matrix.

Inputs:
    configs/v12/systemb_b85_f4_n24_decision.yaml and the compact F3c evidence
    files declared in that config.

Outputs:
    F4 hourly stability summary, cell stability scorecard, robust priority
    cells, neutral-boundary cells, unstable-review cells, target card, N150
    recommendation, surrogate role decision, geometry uncertainty register,
    decision matrix, report, Chinese note, and status Markdown.

Saved metrics:
    Decision status, core-hour stability headline, h10 caveat headline, robust
    priority count, neutral-boundary count, unstable-review count, N150
    recommendation, surrogate role decision, B9 status, and created files.

This runner does not stage, commit, run QGIS, run SOLWEIG, read/copy/write
rasters, copy/open svfs.zip, create local WBGT, create hazard_score/risk_score,
create AOI-wide prediction, create System A/B coupling output, create an N150
manifest/runner, train a surrogate, or perform Tmrt-to-WBGT conversion.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from v12_b85_f4_n24_decision_matrix import DEFAULT_CONFIG, F4_PARTIAL, F4_PASS, rel, run


def main() -> int:
    """Parse CLI args and run the F4 decision matrix."""
    parser = argparse.ArgumentParser(
        description=(
            "Create B8.5-F4 N24 decision artifacts from compact F3c evidence. "
            "Does not run QGIS/SOLWEIG, read rasters, or create WBGT/risk/N150 "
            "execution outputs."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="B8.5-F4 YAML config path.")
    args = parser.parse_args()
    result = run(args.config)
    print(f"Status: {result.decision_status}")
    print(f"Core-hour stability headline: {result.core_hour_headline}")
    print(f"h10 caveat headline: {result.h10_caveat_headline}")
    print(f"Robust priority cell count: {result.robust_priority_count}")
    print(f"Neutral-boundary cell count: {result.neutral_boundary_count}")
    print(f"Unstable-review cell count: {result.unstable_review_count}")
    print(f"N150 recommendation: {result.n150_recommendation}")
    print(f"Surrogate role decision: {result.surrogate_role_decision}")
    print(f"B9 status: {result.b9_status}")
    print("Files created:")
    for path in result.files_created:
        print(f"- {rel(path)}")
    return 0 if result.decision_status in {F4_PASS, F4_PARTIAL} else 2


if __name__ == "__main__":
    raise SystemExit(main())
