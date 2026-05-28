"""B87F2 source inventory wrapper.

Inputs:
    --config configs/v12/systemb_b87f2_true_vector_feature_patch.yaml

Outputs:
    All B87F2 compact CSV/Markdown artifacts, including
    b87f2_source_inventory.csv and b87f2_source_readiness_matrix.csv.

Saved metrics:
    Local compact/vector source existence, safety status, feature-gap
    resolution, model retest metrics, and stop/go decision.
"""

from v12_b87f2_common import wrapper_cli


if __name__ == "__main__":
    raise SystemExit(wrapper_cli("source_inventory"))
