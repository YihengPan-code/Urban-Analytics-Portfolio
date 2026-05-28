"""Run B8.7b.2 discovery by delegating to the resolver-compatible modules.

Inputs:
    configs/v12/systemb_b87b2_cross_worktree_asset_discovery.yaml.
Outputs:
    Compact B8.7b.2 metadata CSV/Markdown artifacts under the discovery output
    directory. This script does not open rasters, run QGIS/SOLWEIG, create a
    run-ready manifest, create a runner, copy/move/symlink assets, or create
    AOI/B9/WBGT/risk/System A-B coupling outputs.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from v12_b87b2_asset_mapping_builder import run as run_asset_mapping_builder
from v12_b87b2_asset_signature import run as run_asset_signature
from v12_b87b2_cell_folder_discovery import run as run_cell_folder_discovery
from v12_b87b2_input_inventory import DEFAULT_CONFIG, run as run_input_inventory
from v12_b87b2_mapping_plan import run as run_mapping_plan
from v12_b87b2_readiness_decision import run as run_readiness_decision
from v12_b87b2_search_roots import run as run_search_roots


def run(config_path: Path = DEFAULT_CONFIG):
    """Run all B8.7b.2 metadata-only discovery steps."""
    inventory = run_input_inventory(config_path)
    print(inventory)
    if inventory.status == "FAIL":
        return inventory
    roots = run_search_roots(config_path)
    print(roots)
    folders = run_cell_folder_discovery(config_path)
    print(folders)
    signatures = run_asset_signature(config_path)
    print(signatures)
    mappings = run_asset_mapping_builder(config_path)
    print(mappings)
    plan = run_mapping_plan(config_path)
    print(f"mapping_plan_rows={len(plan)}")
    decision = run_readiness_decision(config_path)
    print(decision)
    return decision


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run B8.7b.2 cross-worktree asset discovery; metadata only, no raster IO."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
