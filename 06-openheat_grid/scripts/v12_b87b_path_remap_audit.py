"""Audit B8.7b local path remap readiness without copying assets.

Inputs:
    configs/v12/systemb_b87b_n300_execution_precheck.yaml plus prior B8.5-F2b
    and F2d root/path-remap compact CSVs.
Outputs:
    b87b_local_path_remap_audit.csv.
Saved metrics:
    Prior root aliases, local expected roots, metadata-only existence checks,
    commit-safety labels, action required for future B8.7c, and explicit
    local_audit_only scope. This script does not copy files, open rasters, open
    svfs.zip, create symlinks, create runners, or run QGIS/SOLWEIG.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from v12_b87b_input_inventory import CLAIM_BOUNDARY, DEFAULT_CONFIG, clean
from v12_b87b_input_inventory import load_config, out_path, path_exists_metadata, read_csv_rows, write_csv_rows


@dataclass(frozen=True)
class PathRemapAuditResult:
    """B8.7b path-remap audit result."""

    status: str
    rows: int
    unresolved_items: int
    headline: str


def add_path_row(
    rows: list[dict[str, Any]],
    asset_key: str,
    repo_reference_path: str,
    local_expected_path: str,
    path_kind: str,
    safe_to_commit_path_metadata: str,
    action_required: str,
    source: str,
    check_exists: bool = True,
) -> None:
    """Append one path-remap audit row."""
    exists = "unknown"
    if check_exists and local_expected_path and "<" not in local_expected_path and "TO_BE_SELECTED" not in local_expected_path:
        exists, _ = path_exists_metadata(local_expected_path)
    rows.append(
        {
            "asset_key": asset_key,
            "repo_reference_path": repo_reference_path,
            "local_expected_path": local_expected_path,
            "exists_by_metadata_check": exists,
            "path_kind": path_kind,
            "safe_to_commit_path_metadata": safe_to_commit_path_metadata,
            "action_required": action_required,
            "source": source,
            "metadata_scope": "local_audit_only",
            "claim_boundary": CLAIM_BOUNDARY,
        }
    )


def run(config_path: Path = DEFAULT_CONFIG) -> PathRemapAuditResult:
    """Create the B8.7b path remap audit."""
    config = load_config(config_path)
    rows: list[dict[str, Any]] = []

    f2d_roots = read_csv_rows(config["f2d_root_inventory_path"])
    for root in f2d_roots:
        alias = clean(root.get("root_alias"))
        root_path = clean(root.get("root_path"))
        safe = "yes" if clean(root.get("commit_safe_to_reference")).lower() in {"true", "yes"} else "no"
        action = "reuse as local_audit_only reference; do not copy assets"
        if clean(root.get("status")) != "PASS":
            action = "human local remap review required before B8.7c"
        add_path_row(
            rows,
            asset_key=f"prior_root_{alias}",
            repo_reference_path=f"<{alias}>",
            local_expected_path=root_path,
            path_kind=clean(root.get("root_kind")) or "prior_root",
            safe_to_commit_path_metadata=safe,
            action_required=action,
            source="b85_f2d_root_inventory",
        )

    for log_path in config.get("local_run_log_candidates", []):
        add_path_row(
            rows,
            asset_key="prior_f5_local_run_log",
            repo_reference_path="outputs/v12_surrogate/b8_5_f5_n150_multiforcing/B8_5_F5_STATUS.md",
            local_expected_path=clean(log_path),
            path_kind="local_run_log_csv",
            safe_to_commit_path_metadata="yes",
            action_required="use for runtime summary only; do not commit raw local log",
            source="config.local_run_log_candidates",
        )

    add_path_row(
        rows,
        asset_key="future_b87c_local_output_root_placeholder",
        repo_reference_path="not_created_in_B87B",
        local_expected_path="C:/OpenHeat-local/solweig/b87c_n300",
        path_kind="future_local_output_root",
        safe_to_commit_path_metadata="yes",
        action_required="future B8.7c may create/check this local-only root only after explicit authorization",
        source="B87B_precheck_recommendation",
    )
    add_path_row(
        rows,
        asset_key="future_b87c_asset_root_placeholder",
        repo_reference_path="data/solweig paths are not commit-safe and not created in B87B",
        local_expected_path="LOCAL_ONLY_TO_BE_SELECTED_BY_B87C",
        path_kind="future_local_asset_root",
        safe_to_commit_path_metadata="yes",
        action_required="resolve local root and path aliases in B8.7c; no asset copy in B8.7b",
        source="B87B_precheck_recommendation",
        check_exists=False,
    )
    add_path_row(
        rows,
        asset_key="future_new_cell_tile_pattern",
        repo_reference_path="data/solweig/v12_n300_tiles/<cell_id>",
        local_expected_path="C:/OpenHeat-local/solweig/b87c_n300/assets/<cell_id>",
        path_kind="future_cell_asset_pattern",
        safe_to_commit_path_metadata="yes",
        action_required="schema/pattern only; not a resolved run-ready path and not checked as a file",
        source="B87B_precheck_recommendation",
        check_exists=False,
    )
    add_path_row(
        rows,
        asset_key="future_pre_manifest_schema_only",
        repo_reference_path="outputs/v12_surrogate/b8_7b_n300_execution_precheck/b87b_pre_manifest_schema_preview.csv",
        local_expected_path="not_applicable",
        path_kind="schema_preview_not_manifest",
        safe_to_commit_path_metadata="yes",
        action_required="keep schema preview non-executable; no B87B manifest",
        source="B87B_precheck_output",
        check_exists=False,
    )

    write_csv_rows(
        out_path(config, "b87b_local_path_remap_audit.csv"),
        rows,
        [
            "asset_key",
            "repo_reference_path",
            "local_expected_path",
            "exists_by_metadata_check",
            "path_kind",
            "safe_to_commit_path_metadata",
            "action_required",
            "source",
            "metadata_scope",
            "claim_boundary",
        ],
    )
    unresolved = sum(1 for row in rows if row["exists_by_metadata_check"] in {"no", "unknown"})
    status = "UNKNOWN_LOCAL_AUDIT_REQUIRED" if unresolved else "PASS"
    headline = f"{len(rows)} path/remap rows audited; {unresolved} unresolved or placeholder-only rows."
    return PathRemapAuditResult(status=status, rows=len(rows), unresolved_items=unresolved, headline=headline)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Audit prior local root/path remap readiness for B8.7b using metadata "
            "checks only. Does not copy/open raster assets or create runners."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
