"""Run B87F2 true-vector feature patch, benchmark retest, and stop/go decision.

Inputs:
    --config configs/v12/systemb_b87f2_true_vector_feature_patch.yaml

Outputs:
    Required compact B87F2 CSV/Markdown artifacts under
    outputs/v12_surrogate/b87f2_true_vector_feature_patch/ and the valid UTF-8
    Chinese note under docs/v12/.

Saved metrics:
    Source inventory/readiness, feature gaps, cell geometry, true-vector and
    interaction features, patched matrix/schema/missingness/leakage, ablation
    and model registries, split metrics, predictions, transfer/rank audits,
    strata errors, prior comparisons, promotion/AOI/stop-go decisions, status,
    report, and next-lane prompt.
"""

from v12_b87f2_common import main_runner


if __name__ == "__main__":
    raise SystemExit(main_runner())
