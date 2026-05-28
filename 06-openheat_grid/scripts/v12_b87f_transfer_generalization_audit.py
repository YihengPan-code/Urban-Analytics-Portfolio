"""B87F transfer generalization audit wrapper.

Inputs:
    B87F model metrics summary and B87E prior old-to-new metrics.

Outputs:
    b87f_transfer_generalization_matrix.csv plus dependent compact artifacts.

Saved metrics:
    Old-to-new and new-to-old MAE/RMSE/Spearman, degradation ratio against
    B87E best old-to-new, and 5% transfer gate status.
"""

from __future__ import annotations

from v12_b87f_common import wrapper_cli


if __name__ == "__main__":
    raise SystemExit(wrapper_cli("transfer_generalization_audit"))
