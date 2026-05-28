"""Compatibility entry point for B8.7b.2 cell asset discovery.

Inputs:
    B8.7b.2 config and candidate/search-root CSVs.
Outputs:
    b87b2_cell_folder_candidates.csv.
Saved metrics:
    Same metadata-only folder candidate metrics as
    `v12_b87b2_cell_folder_discovery.py`. This wrapper exists under the
    requested lane filename and performs no raster IO, QGIS/SOLWEIG execution,
    copy, move, symlink, manifest, or runner creation.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from v12_b87b2_cell_folder_discovery import run
from v12_b87b2_input_inventory import DEFAULT_CONFIG


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run B8.7b.2 cell asset discovery by metadata only; no raster IO."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
