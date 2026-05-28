"""B87F patch model evaluation wrapper.

Inputs:
    B87F patch model predictions and split-level metrics generated from the
    configured N150-compatible registry.

Outputs:
    b87f_patch_model_metrics_summary.csv plus dependent compact B87F artifacts.

Saved metrics:
    Fold-averaged MAE, RMSE, bias, R2, median/p90 absolute error, rank
    correlation, sign agreement, and top-k overlap by feature set/model/split.
"""

from __future__ import annotations

from v12_b87f_common import wrapper_cli


if __name__ == "__main__":
    raise SystemExit(wrapper_cli("evaluate_patch_models"))
