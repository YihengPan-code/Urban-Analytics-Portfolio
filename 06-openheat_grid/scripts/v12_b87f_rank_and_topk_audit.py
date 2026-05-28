"""B87F rank and top-k audit wrapper.

Inputs:
    B87F split-level predictions and rank/top-k metrics.

Outputs:
    b87f_rank_topk_matrix.csv plus dependent compact B87F artifacts.

Saved metrics:
    Spearman rank correlation and top10/top20/top30/top-decile overlap by
    feature set, model, and split family. These are prioritisation diagnostics
    only, not hazard/risk claims.
"""

from __future__ import annotations

from v12_b87f_common import wrapper_cli


if __name__ == "__main__":
    raise SystemExit(wrapper_cli("rank_and_topk_audit"))
