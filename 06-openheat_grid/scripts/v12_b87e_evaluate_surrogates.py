"""B87E surrogate evaluation wrapper.

Inputs, outputs, config path, saved metrics, and claim boundaries are declared
in scripts/v12_b87e_common.py. This step ensures evaluation metrics and rank
diagnostics are written for the N300 surrogate benchmark.
"""

from __future__ import annotations

from v12_b87e_common import wrapper_cli


if __name__ == "__main__":
    raise SystemExit(wrapper_cli("evaluate_surrogates"))
