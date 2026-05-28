"""B87F target and error diagnosis wrapper.

Inputs:
    B87E feature matrix, predictions, error strata, target labels, and B8.6g3
    source-gap context declared by the B87F config.

Outputs:
    b87f_target_distribution_deepdive.csv and
    b87f_error_source_hypotheses.csv plus dependent compact B87F artifacts.

Saved metrics:
    Target distribution by sample/context/typology/spatial strata and concise
    non-causal hypotheses for prior error sources and feature gaps.
"""

from __future__ import annotations

from v12_b87f_common import wrapper_cli


if __name__ == "__main__":
    raise SystemExit(wrapper_cli("target_error_diagnosis"))
