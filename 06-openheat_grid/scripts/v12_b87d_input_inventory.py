"""B87D input inventory wrapper.

Inputs, outputs, config path, saved metrics, and claim boundaries are declared
in scripts/v12_b87d_common.py. This step writes input, run-log, and manifest
audit CSVs and does not run QGIS/SOLWEIG or write raster assets.
"""

from __future__ import annotations

from v12_b87d_common import wrapper_cli


if __name__ == "__main__":
    raise SystemExit(wrapper_cli("input_inventory"))
