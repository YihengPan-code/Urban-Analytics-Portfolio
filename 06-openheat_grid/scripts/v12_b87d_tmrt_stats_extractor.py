"""B87D Tmrt compact statistics wrapper.

Inputs, outputs, config path, saved metrics, and claim boundaries are declared
in scripts/v12_b87d_common.py. This step reads existing local Tmrt rasters for
full-tile finite non-nodata statistics and writes no raster assets.
"""

from __future__ import annotations

from v12_b87d_common import wrapper_cli


if __name__ == "__main__":
    raise SystemExit(wrapper_cli("tmrt_stats_extractor"))
