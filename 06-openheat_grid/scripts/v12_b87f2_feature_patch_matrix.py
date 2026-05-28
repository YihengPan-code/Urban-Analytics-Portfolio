"""B87F2 patched feature matrix wrapper.

Inputs:
    --config configs/v12/systemb_b87f2_true_vector_feature_patch.yaml

Outputs:
    All B87F2 compact CSV/Markdown artifacts, including
    b87f2_patched_feature_matrix.csv, schema, and missingness audit.

Saved metrics:
    Patched matrix shape, missingness, leakage audit, surrogate metrics, and
    stop/go decision.
"""

from v12_b87f2_common import wrapper_cli


if __name__ == "__main__":
    raise SystemExit(wrapper_cli("feature_patch_matrix"))
