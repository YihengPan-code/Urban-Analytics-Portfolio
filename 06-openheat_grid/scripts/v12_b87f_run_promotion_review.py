"""Run the complete B87F N300 surrogate promotion review.

Inputs:
    configs/v12/systemb_b87f_n300_surrogate_promotion_review.yaml, B87D N300
    label integration artifacts, B87E surrogate benchmark artifacts, and compact
    B8.6g/B8.6g3 feature/source context.

Outputs:
    Required B87F CSV/Markdown artifacts under
    outputs/v12_surrogate/b87f_n300_surrogate_promotion_review/ and the Chinese
    companion note under docs/v12.

Saved metrics:
    Input inventory, B87E replay, target/error diagnosis, feature audits,
    feature-set registry, split stress tests, N150-compatible patch model
    metrics/predictions, transfer/rank/top-k/strata/outlier diagnostics,
    prior-candidate comparison, stability audit, promotion review, AOI preflight
    gate, blocker register, model-card patch, status, report, and next prompt.
"""

from __future__ import annotations

from v12_b87f_common import main_runner


if __name__ == "__main__":
    raise SystemExit(main_runner())
