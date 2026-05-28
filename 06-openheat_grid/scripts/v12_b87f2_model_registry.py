"""B87F2 model registry wrapper.

Inputs:
    --config configs/v12/systemb_b87f2_true_vector_feature_patch.yaml

Outputs:
    All B87F2 compact CSV/Markdown artifacts, including
    b87f2_model_registry.csv.

Saved metrics:
    N150-compatible headline model registry and downstream model retest
    metrics. No new headline model families are introduced.
"""

from v12_b87f2_common import wrapper_cli


if __name__ == "__main__":
    raise SystemExit(wrapper_cli("model_registry"))
