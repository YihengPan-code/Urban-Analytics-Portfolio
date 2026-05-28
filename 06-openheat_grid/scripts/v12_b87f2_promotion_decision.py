"""B87F2 promotion decision wrapper.

Inputs:
    --config configs/v12/systemb_b87f2_true_vector_feature_patch.yaml

Outputs:
    All B87F2 compact CSV/Markdown artifacts, including
    b87f2_model_promotion_review.csv, b87f2_aoi_preflight_gate_matrix.csv,
    b87f2_blocker_register.csv, and b87f2_stop_or_continue_decision.csv.

Saved metrics:
    Meaningful-improvement gates, leakage/source gates, AOI preflight gate,
    blocker register, and next-lane recommendation.
"""

from v12_b87f2_common import wrapper_cli


if __name__ == "__main__":
    raise SystemExit(wrapper_cli("promotion_decision"))
