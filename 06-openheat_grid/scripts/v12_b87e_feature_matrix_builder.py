"""B87E feature matrix builder wrapper.

Inputs, outputs, config path, saved metrics, and claim boundaries are declared
in scripts/v12_b87e_common.py. This step joins N300 labels with compact
static/context features and excludes leakage columns from the main feature set.
"""

from __future__ import annotations

from v12_b87e_common import wrapper_cli


if __name__ == "__main__":
    raise SystemExit(wrapper_cli("feature_matrix_builder"))
