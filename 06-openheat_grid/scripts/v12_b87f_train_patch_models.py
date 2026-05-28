"""B87F patch model training wrapper.

Inputs:
    B87E feature matrix, B87F feature sets, B87F split stress tests, and the
    N150-compatible model registry declared by the B87F config.

Outputs:
    b87f_patch_model_metrics_by_split.csv, b87f_patch_predictions_oof.csv, and
    b87f_patch_predictions_holdout.csv plus dependent compact artifacts.

Saved metrics:
    MAE, RMSE, bias, R2, median absolute error, p90 absolute error, Spearman,
    Pearson, top-k overlap, and sign agreement for each controlled comparison.
"""

from __future__ import annotations

from v12_b87f_common import wrapper_cli


if __name__ == "__main__":
    raise SystemExit(wrapper_cli("train_patch_models"))
