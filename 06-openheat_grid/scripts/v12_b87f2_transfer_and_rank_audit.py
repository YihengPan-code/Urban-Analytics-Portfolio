"""B87F2 transfer and rank audit wrapper.

Inputs:
    --config configs/v12/systemb_b87f2_true_vector_feature_patch.yaml

Outputs:
    All B87F2 compact CSV/Markdown artifacts, including
    b87f2_transfer_generalization_matrix.csv and b87f2_rank_topk_matrix.csv.

Saved metrics:
    Old-to-new, new-to-old, rank Spearman, and top-k overlap diagnostics.
"""

from v12_b87f2_common import wrapper_cli


if __name__ == "__main__":
    raise SystemExit(wrapper_cli("transfer_and_rank_audit"))
