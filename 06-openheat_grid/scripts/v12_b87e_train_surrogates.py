"""B87E surrogate training wrapper.

Inputs, outputs, config path, saved metrics, and claim boundaries are declared
in scripts/v12_b87e_common.py. This step runs the compact sklearn surrogate
benchmark and writes metrics/predictions; it creates no AOI/B9/WBGT/risk output.
"""

from __future__ import annotations

from v12_b87e_common import wrapper_cli


if __name__ == "__main__":
    raise SystemExit(wrapper_cli("train_surrogates"))
