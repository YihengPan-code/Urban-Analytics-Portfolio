"""B87F2 feature ablation registry wrapper.

Inputs:
    --config configs/v12/systemb_b87f2_true_vector_feature_patch.yaml

Outputs:
    All B87F2 compact CSV/Markdown artifacts, including
    b87f2_feature_ablation_registry.csv.

Saved metrics:
    B87E baseline, full patch, no-coordinate, interaction-only, family
    ablation, proxy-only, and pruned-best-effort feature sets.
"""

from v12_b87f2_common import wrapper_cli


if __name__ == "__main__":
    raise SystemExit(wrapper_cli("feature_ablation_registry"))
