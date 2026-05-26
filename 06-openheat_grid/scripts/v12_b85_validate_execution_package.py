"""Validate the B8.5-F1 QGIS/SOLWEIG execution package.

Inputs:
    configs/v12/systemb_b85_f1_execution_package.yaml
    B8.5-F0 run matrix, selected forcing days, N24 cell contract, and compact
    B8.5-F1 package artifacts declared in the config.

Outputs:
    outputs/v12_surrogate/b8_5_execution_package/b85_f1_manifest_validation.csv
    Console summary of package status, manifest row count, asset readiness,
    QGIS/SOLWEIG execution flag, and missing package artifacts if any.

Saved metrics:
    Manifest validation checks, required package artifact existence, and
    forbidden-file status for changed files in this worktree.

This validator does not run QGIS, run SOLWEIG, create rasters, copy rasters,
create local WBGT, create hazard/risk scores, stage files, or commit files.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from v12_b85_prepare_execution_package import (
    BLOCKED,
    FAILED,
    NO,
    PARTIAL,
    PASS,
    artifact_paths,
    build_asset_inventory,
    package_status,
    read_config,
    rel,
    repo_path,
    validate_manifest,
    write_csv_rows,
)


DEFAULT_CONFIG = Path("configs/v12/systemb_b85_f1_execution_package.yaml")


def git_status_short() -> list[str]:
    """Return short Git status lines under the current OpenHeat subdirectory."""
    completed = subprocess.run(
        ["git", "status", "--short", "--", "."],
        cwd=repo_path("."),
        check=False,
        capture_output=True,
        text=True,
    )
    return [line.rstrip() for line in completed.stdout.splitlines() if line.strip()]


def changed_forbidden_paths(status_lines: list[str]) -> list[str]:
    """Identify forbidden changed files from git status output."""
    forbidden_fragments = [
        "data/solweig/",
        "data/rasters/",
        "data/archive/",
        "svfs.zip",
        "hourly_grid_heatstress_forecast",
    ]
    forbidden_suffixes = (".tif", ".tiff")
    hits: list[str] = []
    for line in status_lines:
        path = line[3:].replace("\\", "/")
        lower = path.lower()
        if lower.endswith(forbidden_suffixes) or any(fragment in lower for fragment in forbidden_fragments):
            hits.append(path)
    return hits


def artifact_check_rows(paths: list[Path]) -> list[dict[str, str]]:
    """Build artifact-existence validation rows."""
    rows: list[dict[str, str]] = []
    for path in paths:
        rows.append(
            {
                "section": "package_artifact",
                "check_name": rel(path),
                "status": PASS if path.exists() else FAILED,
                "expected": "exists",
                "observed": "exists" if path.exists() else "missing",
                "detail": "",
            }
        )
    return rows


def forbidden_check_row(status_lines: list[str]) -> dict[str, str]:
    """Build a validation row for forbidden changed files."""
    hits = changed_forbidden_paths(status_lines)
    return {
        "section": "git_safety",
        "check_name": "no_forbidden_files_touched",
        "status": PASS if not hits else FAILED,
        "expected": "no changed forbidden files",
        "observed": "none" if not hits else "; ".join(hits),
        "detail": "Checks changed paths visible to git status under the OpenHeat subdirectory.",
    }


def validate(config_path: Path) -> int:
    """Run package validation and return a process exit code."""
    config = read_config(repo_path(config_path))
    manifest_rows, manifest_count, manifest_ok = validate_manifest(config)
    inventory, asset_status = build_asset_inventory(config)
    artifacts = artifact_paths(config)
    artifact_rows = artifact_check_rows(artifacts)
    status_lines = git_status_short()
    safety_row = forbidden_check_row(status_lines)
    outputs = config["outputs"]
    all_rows = manifest_rows + artifact_rows + [safety_row]
    write_csv_rows(
        repo_path(outputs["manifest_validation"]),
        all_rows,
        ["section", "check_name", "status", "expected", "observed", "detail"],
    )

    artifacts_ok = all(row["status"] == PASS for row in artifact_rows)
    forbidden_ok = safety_row["status"] == PASS
    overall = package_status(manifest_ok and artifacts_ok and forbidden_ok, asset_status)
    if overall == PASS and asset_status in {PARTIAL, "READY"}:
        exit_code = 0
    elif overall == BLOCKED:
        exit_code = 2
    else:
        exit_code = 1

    print(f"Status: {overall}")
    print(f"Manifest row count: {manifest_count}")
    print(f"Asset readiness status: {asset_status}")
    print(f"QGIS/SOLWEIG executed: {NO}")
    print(f"Package artifacts present: {'yes' if artifacts_ok else 'no'}")
    print(f"Forbidden files touched: {safety_row['observed']}")
    print(f"Inventory rows: {len(inventory)}")
    return exit_code


def main() -> int:
    """Parse CLI arguments and validate the execution package."""
    parser = argparse.ArgumentParser(
        description=(
            "Validate the B8.5-F1 execution package manifest, compact artifacts, "
            "asset readiness, and forbidden-file safety. Does not run QGIS/SOLWEIG."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="B8.5-F1 YAML config path.")
    args = parser.parse_args()
    return validate(args.config)


if __name__ == "__main__":
    raise SystemExit(main())
