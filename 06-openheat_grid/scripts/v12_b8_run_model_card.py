"""Run the B8.3 System B surrogate model-card generator.

Inputs:
    configs/v12/systemb_surrogate_b8_model_card.yaml
    Existing B8.0 feature contract artifacts and B8.2 benchmark metrics declared
    in the config.

Outputs:
    docs/v12/OpenHeat_SystemB_surrogate_model_card_CN.md
    Compact CSV/Markdown artifacts under outputs/v12_surrogate/b8_model_card/.

Saved metrics:
    Candidate model evidence, split-family decision matrix, feature contract
    summary, promotion gate checklist, concise decision report, and
    B8_3_MODEL_CARD_STATUS.md.

This runner does not stage, commit, train models, create AOI-wide predictions,
compute local WBGT, create hazard_score/risk_score, or couple System A and
System B.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from v12_b8_make_model_card import DEFAULT_CONFIG, run
from v12_b8_prepare_surrogate_dataset import repo_path


def main() -> None:
    """Parse CLI args and run the B8.3 model-card workflow."""
    parser = argparse.ArgumentParser(
        description=(
            "Create the B8.3 System B surrogate model card and promotion gate "
            "from existing B8.0/B8.2 artifacts. No model training or AOI "
            "inference is performed."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Model-card YAML config path.")
    args = parser.parse_args()
    command = f"{Path(sys.executable).as_posix()} scripts/v12_b8_run_model_card.py --config {args.config.as_posix()}"
    result = run(repo_path(args.config), commands=[command])
    print(f"Status: {result.status}")
    print(f"Candidate model: {result.candidate_model}")
    print(f"Primary evidence: {result.primary_evidence}")
    print(f"Blockers: {'; '.join(result.blockers)}")
    print(f"Recommended next gate: {result.recommended_next_gate}")
    print("Files created:")
    for path in result.files_created:
        print(f"- {path}")
    print(f"Status file: {result.status_path}")


if __name__ == "__main__":
    main()
