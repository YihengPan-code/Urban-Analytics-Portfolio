"""B87F2 interaction feature builder wrapper.

Inputs:
    --config configs/v12/systemb_b87f2_true_vector_feature_patch.yaml

Outputs:
    All B87F2 compact CSV/Markdown artifacts, including
    b87f2_interaction_features_by_cell.csv.

Saved metrics:
    Tree-building, overhead-pedestrian, water-context, and morphology proxy
    interactions, surrogate metrics, and stop/go decision.
"""

from v12_b87f2_common import wrapper_cli


if __name__ == "__main__":
    raise SystemExit(wrapper_cli("interaction_feature_builder"))
