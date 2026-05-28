"""B87F2 true-vector feature builder wrapper.

Inputs:
    --config configs/v12/systemb_b87f2_true_vector_feature_patch.yaml

Outputs:
    All B87F2 compact CSV/Markdown artifacts, including
    b87f2_true_vector_features_by_cell.csv.

Saved metrics:
    Centroid-buffer true-vector/proxy features by cell, source gaps,
    surrogate retest metrics, and stop/go decision.
"""

from v12_b87f2_common import wrapper_cli


if __name__ == "__main__":
    raise SystemExit(wrapper_cli("true_vector_feature_builder"))
