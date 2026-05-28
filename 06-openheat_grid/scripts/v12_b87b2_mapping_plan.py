"""Normalize B8.7b.2 mappings and write the remap plan.

Inputs:
    b87b2_candidate_asset_mapping.csv produced by metadata-only asset mapping.
Outputs:
    Normalized b87b2_candidate_asset_mapping.csv with the requested columns,
    b87b2_remap_plan.csv, and b87b2_local_only_materialization_options.csv.
Saved metrics:
    Per-cell status, required/desired gaps, selected source folder, target
    B87c folder, recommended materialization method, and authorization flags.
    This is plan-only: it does not copy, move, symlink, open, or generate any
    raster and does not run QGIS/SOLWEIG or create a manifest/runner.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from v12_b87b2_input_inventory import CLAIM_BOUNDARY, DEFAULT_CONFIG, clean, load_config, out_path
from v12_b87b2_input_inventory import read_csv_rows, write_csv_rows


def truth(value: str) -> bool:
    """Return true for yes/true flags."""
    return clean(value).lower() in {"yes", "true", "1"}


def norm_bool(value: bool) -> str:
    """Return lowercase true/false."""
    return "true" if value else "false"


def normalize_status(row: dict[str, str]) -> str:
    """Translate mapping status to the requested discovery status vocabulary."""
    current = clean(row.get("mapping_status"))
    has_svf = truth(row.get("has_svf", ""))
    has_dsm = truth(row.get("has_dsm", ""))
    has_cdsm = truth(row.get("has_cdsm", ""))
    has_dem = truth(row.get("has_dem", ""))
    has_landcover = truth(row.get("has_landcover", ""))
    if current == "AMBIGUOUS_REVIEW":
        return current
    if current in {"UNRESOLVED_NOT_FOUND", "ROOT_INACCESSIBLE"}:
        return current
    if has_svf and has_dsm and has_cdsm and has_dem and has_landcover:
        return "RESOLVED_COMPLETE"
    if has_svf and has_dsm:
        return "RESOLVED_MINIMAL_SVF_DSM"
    if clean(row.get("selected_asset_folder")) or clean(row.get("selected_source_folder")):
        return "RESOLVED_PARTIAL"
    return current or "UNRESOLVED_NOT_FOUND"


def missing(row: dict[str, str], fields: list[tuple[str, str]]) -> str:
    """Return pipe-separated missing asset kinds."""
    return "|".join(name for name, field in fields if not truth(row.get(field, "")))


def normalize_row(row: dict[str, str]) -> dict[str, Any]:
    """Return one requested mapping row."""
    status = normalize_status(row)
    source_folder = clean(row.get("selected_source_folder")) or clean(row.get("selected_asset_folder"))
    has_required = truth(row.get("has_svf", "")) and truth(row.get("has_dsm", ""))
    if status in {"RESOLVED_COMPLETE", "RESOLVED_MINIMAL_SVF_DSM"}:
        method = "reference_existing_path"
    elif status == "RESOLVED_PARTIAL":
        method = "regenerate_assets"
    elif status == "UNRESOLVED_NOT_FOUND":
        method = "regenerate_assets"
    else:
        method = "manual_review"
    return {
        "cell_id": clean(row.get("cell_id")),
        "mapping_status": status,
        "selected_source_folder": source_folder,
        "source_root": clean(row.get("source_root")),
        "has_svf": norm_bool(truth(row.get("has_svf", ""))),
        "has_dsm": norm_bool(truth(row.get("has_dsm", ""))),
        "has_cdsm": norm_bool(truth(row.get("has_cdsm", ""))),
        "has_dem": norm_bool(truth(row.get("has_dem", ""))),
        "has_landcover": norm_bool(truth(row.get("has_landcover", ""))),
        "missing_required_asset_kinds": missing(row, [("svf", "has_svf"), ("dsm", "has_dsm")]),
        "missing_desired_asset_kinds": missing(row, [("cdsm", "has_cdsm"), ("dem", "has_dem"), ("landcover", "has_landcover")]),
        "matched_names_preview": clean(row.get("matched_names_preview")),
        "metadata_only": "true",
        "no_raster_opened": "true",
        "safe_to_materialize_to_b87c_local_root": norm_bool(has_required and status in {"RESOLVED_COMPLETE", "RESOLVED_MINIMAL_SVF_DSM"}),
        "recommended_materialization_method": method,
        "caveat": clean(row.get("caveat")),
        "claim_boundary": CLAIM_BOUNDARY,
    }


def run(config_path: Path = DEFAULT_CONFIG) -> list[dict[str, Any]]:
    """Normalize mappings and write plan-only materialization artifacts."""
    config = load_config(config_path)
    rows = [normalize_row(row) for row in read_csv_rows(out_path(config, "b87b2_candidate_asset_mapping.csv"))]
    mapping_fields = [
        "cell_id",
        "mapping_status",
        "selected_source_folder",
        "source_root",
        "has_svf",
        "has_dsm",
        "has_cdsm",
        "has_dem",
        "has_landcover",
        "missing_required_asset_kinds",
        "missing_desired_asset_kinds",
        "matched_names_preview",
        "metadata_only",
        "no_raster_opened",
        "safe_to_materialize_to_b87c_local_root",
        "recommended_materialization_method",
        "caveat",
        "claim_boundary",
    ]
    write_csv_rows(out_path(config, "b87b2_candidate_asset_mapping.csv"), rows, mapping_fields)

    target_root = clean(config["target_b87c_asset_root"]).rstrip("/\\")
    remap_rows = [
        {
            "cell_id": clean(row.get("cell_id")),
            "target_folder": f"{target_root}/{clean(row.get('cell_id'))}",
            "source_folder": clean(row.get("selected_source_folder")),
            "recommended_method": clean(row.get("recommended_materialization_method")),
            "reason": clean(row.get("caveat")),
            "expected_asset_kinds": "svf|dsm|cdsm|dem|landcover",
            "do_not_commit_to_git": "true",
            "requires_user_authorization": "true",
            "metadata_only": "true",
            "no_raster_opened": "true",
            "claim_boundary": CLAIM_BOUNDARY,
        }
        for row in rows
        if clean(row.get("mapping_status")) in {"RESOLVED_COMPLETE", "RESOLVED_MINIMAL_SVF_DSM"}
    ]
    write_csv_rows(
        out_path(config, "b87b2_remap_plan.csv"),
        remap_rows,
        [
            "cell_id",
            "target_folder",
            "source_folder",
            "recommended_method",
            "reason",
            "expected_asset_kinds",
            "do_not_commit_to_git",
            "requires_user_authorization",
            "metadata_only",
            "no_raster_opened",
            "claim_boundary",
        ],
    )
    option_rows = [
        {
            "cell_id": clean(row.get("cell_id")),
            "mapping_status": clean(row.get("mapping_status")),
            "available_materialization_options": (
                "reference_existing_path|local_only_symlink_or_junction|local_only_copy"
                if clean(row.get("safe_to_materialize_to_b87c_local_root")) == "true"
                else "manual_review|regenerate_assets"
            ),
            "recommended_materialization_method": clean(row.get("recommended_materialization_method")),
            "requires_user_authorization": "true",
            "do_not_commit_to_git": "true",
            "notes": clean(row.get("caveat")),
            "claim_boundary": CLAIM_BOUNDARY,
        }
        for row in rows
    ]
    write_csv_rows(
        out_path(config, "b87b2_local_only_materialization_options.csv"),
        option_rows,
        [
            "cell_id",
            "mapping_status",
            "available_materialization_options",
            "recommended_materialization_method",
            "requires_user_authorization",
            "do_not_commit_to_git",
            "notes",
            "claim_boundary",
        ],
    )
    return rows


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Write B8.7b.2 remap plan only; no materialization.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(f"mapping_plan_rows={len(run(args.config))}")


if __name__ == "__main__":
    main()
