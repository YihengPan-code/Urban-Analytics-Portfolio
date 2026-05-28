"""B87F feature group registry wrapper.

Inputs:
    B87E feature matrix and feature schema declared by the B87F config.

Outputs:
    b87f_feature_group_registry.csv plus dependent compact B87F artifacts.

Saved metrics:
    Column-level inferred feature family, B87E role, B87E inclusion flag,
    predictor eligibility, and leakage/drop reason.
"""

from __future__ import annotations

from v12_b87f_common import wrapper_cli


if __name__ == "__main__":
    raise SystemExit(wrapper_cli("feature_group_registry"))
