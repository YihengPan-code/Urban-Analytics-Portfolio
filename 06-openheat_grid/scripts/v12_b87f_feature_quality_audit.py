"""B87F feature quality audit wrapper.

Inputs:
    B87E feature matrix, schema, and leakage policy declared by the B87F config.

Outputs:
    b87f_feature_quality_audit.csv and
    b87f_feature_correlation_clusters.csv plus dependent compact artifacts.

Saved metrics:
    Missingness, cardinality, numeric ratio, zero variance, high-missing flags,
    leakage policy reason, high-dimensional risk note, and correlation clusters.
"""

from __future__ import annotations

from v12_b87f_common import wrapper_cli


if __name__ == "__main__":
    raise SystemExit(wrapper_cli("feature_quality_audit"))
