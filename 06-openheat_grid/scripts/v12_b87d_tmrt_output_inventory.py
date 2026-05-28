"""B87D Tmrt output inventory wrapper.

Inputs, outputs, config path, saved metrics, and claim boundaries are declared
in scripts/v12_b87d_common.py. This step locates existing local Tmrt rasters
for read-only statistics and writes no raster assets.
"""

from __future__ import annotations

from v12_b87d_common import wrapper_cli


if __name__ == "__main__":
    raise SystemExit(wrapper_cli("tmrt_output_inventory"))
