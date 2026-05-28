"""B87E error strata wrapper.

Inputs, outputs, config path, saved metrics, and claim boundaries are declared
in scripts/v12_b87e_common.py. This step writes compact error-by-strata tables
from GroupKFold out-of-fold predictions.
"""

from __future__ import annotations

from v12_b87e_common import wrapper_cli


if __name__ == "__main__":
    raise SystemExit(wrapper_cli("error_strata"))
