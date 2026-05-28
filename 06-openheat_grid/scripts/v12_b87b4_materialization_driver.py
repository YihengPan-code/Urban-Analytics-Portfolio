"""Run the local-only B87B4 materialization driver.

Inputs: config, locked grid GeoJSON, candidate index, source rasters/vectors when
rasterio/geopandas are available, and compact forcing CSV.
Outputs: local focus-cell/forcing assets plus b87b4_materialization_execution_log.csv
and materialization audit CSVs.
Saved metrics: per-task status, runtime used, local path, and blocker status.
"""

from __future__ import annotations

from pathlib import Path

from v12_b87b4_b87c_common import build_parser, run_named_step


if __name__ == "__main__":
    args = build_parser("Run B87B4 local materialization driver.").parse_args()
    raise SystemExit(run_named_step("materialization_driver", Path(args.config)))
