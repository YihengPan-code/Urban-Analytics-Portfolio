"""Inventory B8.7b.2 cross-worktree search roots by metadata only.

Inputs:
    B8.7b.2 config search roots, current B8 worktree root, main worktree root,
    and local C:/OpenHeat-local roots.
Outputs:
    b87b2_search_root_inventory.csv.
Saved metrics:
    Per-root existence, directory/listability status, top-level file/directory
    counts, root role, and inaccessible errors. This script inspects only path
    metadata and directory names; it never opens raster contents and never runs
    QGIS/SOLWEIG or creates manifests/runners.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from v12_b87b2_input_inventory import CLAIM_BOUNDARY, DEFAULT_CONFIG, clean, effective_search_roots
from v12_b87b2_input_inventory import load_config, out_path, repo_path, root_role, write_csv_rows, yes_no


def inspect_root(config: dict[str, Any], root: str) -> dict[str, Any]:
    """Return one search-root inventory row."""
    path = repo_path(root)
    exists = False
    is_dir = False
    listable = False
    top_dirs = 0
    top_files = 0
    error = ""
    try:
        exists = path.exists()
        is_dir = path.is_dir() if exists else False
        if is_dir:
            for child in path.iterdir():
                listable = True
                if child.is_dir():
                    top_dirs += 1
                elif child.is_file():
                    top_files += 1
    except OSError as exc:
        error = clean(exc)
    return {
        "root_path": root,
        "root_role": root_role(config, root),
        "exists_by_metadata_check": yes_no(exists),
        "is_dir": yes_no(is_dir),
        "listable": yes_no(listable or (exists and is_dir and not error)),
        "top_level_dir_count": top_dirs,
        "top_level_file_count": top_files,
        "included_in_search": yes_no(exists and is_dir and not error),
        "inaccessible_error": error,
        "metadata_only": "true",
        "no_raster_opened": "true",
        "claim_boundary": CLAIM_BOUNDARY,
    }


def run(config_path: Path = DEFAULT_CONFIG) -> list[dict[str, Any]]:
    """Run search-root inventory."""
    config = load_config(config_path)
    rows = [inspect_root(config, root) for root in effective_search_roots(config)]
    write_csv_rows(
        out_path(config, "b87b2_search_root_inventory.csv"),
        rows,
        [
            "root_path",
            "root_role",
            "exists_by_metadata_check",
            "is_dir",
            "listable",
            "top_level_dir_count",
            "top_level_file_count",
            "included_in_search",
            "inaccessible_error",
            "metadata_only",
            "no_raster_opened",
            "claim_boundary",
        ],
    )
    return rows


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Inventory B8.7b.2 search roots by metadata only; no raster IO or QGIS/SOLWEIG."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(f"search_roots={len(run(args.config))}")


if __name__ == "__main__":
    main()
