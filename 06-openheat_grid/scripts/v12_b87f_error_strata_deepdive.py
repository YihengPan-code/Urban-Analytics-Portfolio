"""B87F error strata deep-dive wrapper.

Inputs:
    B87F OOF predictions and B87E feature matrix with diagnostic strata and
    compact physical proxy columns.

Outputs:
    b87f_error_strata_deepdive.csv and
    b87f_outlier_cell_context_register.csv plus dependent compact artifacts.

Saved metrics:
    OOF MAE/RMSE/bias/p90 error by sample group, forcing day, hour, typology,
    spatial bin, primary role, water/river, vegetation, overhead, shade, and
    SVF proxy strata.
"""

from __future__ import annotations

from v12_b87f_common import wrapper_cli


if __name__ == "__main__":
    raise SystemExit(wrapper_cli("error_strata_deepdive"))
