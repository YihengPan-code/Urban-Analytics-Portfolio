"""B87F model-card patch wrapper.

Inputs:
    B87F promotion review, model metrics, feature-set registry, and AOI gate
    matrix.

Outputs:
    b87f_model_card_patch_summary.csv, B87F_STATUS.md, b87f_report.md, and the
    Chinese B87F note plus dependent compact artifacts.

Saved metrics:
    Candidate scope, model/feature-set choice, key GroupKFold metrics, no-pickle
    artifact policy, disallowed-output boundaries, and non-causal caveats.
"""

from __future__ import annotations

from v12_b87f_common import wrapper_cli


if __name__ == "__main__":
    raise SystemExit(wrapper_cli("model_card_patch"))
