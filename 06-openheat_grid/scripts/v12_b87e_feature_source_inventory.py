"""B87E feature source inventory wrapper.

Inputs, outputs, config path, saved metrics, and claim boundaries are declared
in scripts/v12_b87e_common.py. This step inventories compact feature sources
and reads no rasters.
"""

from __future__ import annotations

from v12_b87e_common import wrapper_cli


if __name__ == "__main__":
    raise SystemExit(wrapper_cli("feature_source_inventory"))
