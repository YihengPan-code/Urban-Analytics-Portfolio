"""B87F promotion decision wrapper.

Inputs:
    B87F metrics, transfer matrix, rank/top-k diagnostics, leakage audit,
    strata deep dive, and B8.6g3 AOI/B9 blocker matrix.

Outputs:
    b87f_model_promotion_review.csv, b87f_aoi_preflight_gate_matrix.csv,
    b87f_blocker_register.csv, and b87f_next_lane_decision_matrix.csv plus
    dependent compact artifacts.

Saved metrics:
    Promotion gates for leakage, context/prior comparison, transfer, strata
    stability, rank stability, non-causal interpretability, and AOI source gaps.
"""

from __future__ import annotations

from v12_b87f_common import wrapper_cli


if __name__ == "__main__":
    raise SystemExit(wrapper_cli("promotion_decision"))
