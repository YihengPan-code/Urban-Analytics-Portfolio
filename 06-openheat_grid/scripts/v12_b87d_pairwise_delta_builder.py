"""B87D B87C pairwise delta builder wrapper.

Inputs, outputs, config path, saved metrics, and claim boundaries are declared
in scripts/v12_b87d_common.py. This step builds overhead_as_canopy minus base
SOLWEIG-derived Tmrt labels and does not create WBGT, hazard, risk, AOI, or B9
outputs.
"""

from __future__ import annotations

from v12_b87d_common import wrapper_cli


if __name__ == "__main__":
    raise SystemExit(wrapper_cli("pairwise_delta_builder"))
