"""B87D F5 extraction convention resolver wrapper.

Inputs, outputs, config path, saved metrics, and claim boundaries are declared
in scripts/v12_b87d_common.py. This step recovers the final F5 full-tile valid
non-nodata Tmrt statistic convention and reads no B87C raster pixels.
"""

from __future__ import annotations

from v12_b87d_common import wrapper_cli


if __name__ == "__main__":
    raise SystemExit(wrapper_cli("focus_mask_resolver"))
