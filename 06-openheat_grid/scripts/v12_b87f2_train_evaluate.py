"""B87F2 train/evaluate wrapper.

Inputs:
    --config configs/v12/systemb_b87f2_true_vector_feature_patch.yaml

Outputs:
    All B87F2 compact CSV/Markdown artifacts, including
    b87f2_model_metrics_by_split.csv, b87f2_model_metrics_summary.csv,
    b87f2_predictions_oof.csv, and b87f2_predictions_holdout.csv.

Saved metrics:
    MAE, RMSE, bias, R2, median and p90 absolute error, Spearman, top-k
    overlap, sign agreement, transfer diagnostics, and stop/go decision.
"""

from v12_b87f2_common import wrapper_cli


if __name__ == "__main__":
    raise SystemExit(wrapper_cli("train_evaluate"))
