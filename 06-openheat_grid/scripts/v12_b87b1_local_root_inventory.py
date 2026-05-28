"""Inventory prior and candidate local roots for B8.7b.1.

Inputs:
    configs/v12/systemb_b87b1_local_asset_remap.yaml, optional manual local-root
    CSV, B8.7b path-remap audit, B8.5-F1/F2/F3/F5 docs/configs/outputs, and
    compact prior root inventories.
Outputs:
    outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_prior_local_root_inventory.csv.
Saved metrics:
    Prior/candidate root keys, source files, metadata-only existence/type/size
    checks, manual user status, selected resolution roots, and root gaps. This
    script only scans text files and path metadata; it does not read, open,
    copy, move, create, or write raster files, and does not modify local roots.
"""

from __future__ import annotations

import argparse
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from v12_b87b1_input_inventory import (
    CLAIM_BOUNDARY,
    DEFAULT_CONFIG,
    PROJECT_ROOT,
    TEXT_SCAN_SUFFIXES,
    clean,
    config_list,
    is_forbidden_raster_path,
    load_config,
    out_path,
    path_exists_metadata,
    read_csv_rows,
    rel_path,
    repo_path,
    write_csv_rows,
)


@dataclass(frozen=True)
class LocalRootInventoryResult:
    """B8.7b.1 local-root inventory result."""

    status: str
    rows: int
    manual_local_roots_found: bool
    roots_resolved_count: int


MANUAL_ROOT_KEYS = [
    "b87c_n300_asset_root",
    "b87c_n300_output_root",
    "b85_f1_tiles_root",
    "b85_f2c_met_forcing_root",
    "qgis_manual_check_root",
    "prior_f5_run_log_root",
    "optional_existing_cell_asset_map_csv",
    "optional_tile_index_csv",
]

VALID_USER_STATUS = {"use", "missing", "unknown", "not_applicable"}


def normalize_local_path(raw: str) -> str:
    """Normalize a discovered local path string without checking contents."""
    text = clean(raw).replace("\\", "/")
    text = text.rstrip("`'\"),.;]")
    return text


def infer_root_key(path: str) -> str:
    """Infer a stable local-root key from a known OpenHeat local path."""
    text = normalize_local_path(path).lower()
    if "b87c_n300/assets" in text:
        return "b87c_n300_asset_root"
    if text.endswith("/b87c_n300") or "/b87c_n300/" in text:
        return "b87c_n300_output_root"
    if "b85_f1_tiles" in text:
        return "b85_f1_tiles_root"
    if "met_forcing/b85_f2c" in text:
        return "b85_f2c_met_forcing_root"
    if "qgis_checks" in text:
        return "qgis_manual_check_root"
    if "b85_f5_n150" in text:
        return "prior_f5_run_log_root"
    if "b85_f3a_microbatch" in text:
        return "prior_f3a_microbatch_root"
    if "b85_f3b_onecell" in text:
        return "prior_f3b_onecell_root"
    if "b85_f3c_n24" in text:
        return "prior_f3c_n24_root"
    if "openheat-local/solweig" in text:
        parts = normalize_local_path(path).split("/")
        try:
            idx = [part.lower() for part in parts].index("solweig")
            suffix = "_".join(parts[idx + 1 : idx + 3]) or "solweig"
            return f"discovered_{suffix.lower()}_root"
        except ValueError:
            return "discovered_openheat_local_root"
    if "06-openheat_grid" in text:
        return "prior_original_project_root"
    return "discovered_local_root"


def collapse_to_root(path: str) -> str:
    """Collapse discovered file/output paths to useful local roots."""
    text = normalize_local_path(path)
    lowered = text.lower()
    markers = [
        "b87c_n300/assets",
        "b87c_n300",
        "b85_f1_tiles",
        "met_forcing/b85_f2c",
        "qgis_checks",
        "b85_f5_n150",
        "b85_f3a_microbatch",
        "b85_f3b_onecell",
        "b85_f3c_n24",
    ]
    for marker in markers:
        pos = lowered.find(marker)
        if pos >= 0:
            return text[: pos + len(marker)]
    if "openheat-local/solweig" in lowered:
        parts = text.split("/")
        try:
            idx = [part.lower() for part in parts].index("solweig")
            return "/".join(parts[: idx + 2])
        except ValueError:
            return "C:/OpenHeat-local/solweig"
    return text


def add_root_row(
    rows: list[dict[str, Any]],
    root_key: str,
    candidate_path: str,
    source: str,
    source_file: str,
    required: str,
    user_status: str = "",
    root_kind: str = "local_root_candidate",
    notes: str = "",
) -> None:
    """Append a local-root inventory row with metadata-only checks."""
    exists, is_dir, is_file, parent_exists, size = path_exists_metadata(candidate_path)
    selected = "yes" if required == "yes" and user_status in {"use", ""} and exists == "yes" else "no"
    rows.append(
        {
            "root_key": root_key,
            "candidate_path": candidate_path,
            "source": source,
            "source_file": source_file,
            "required": required,
            "user_status": user_status,
            "exists_by_metadata_check": exists,
            "is_dir": is_dir,
            "is_file": is_file,
            "parent_exists": parent_exists,
            "size_bytes": size,
            "selected_for_resolution": selected,
            "root_kind": root_kind,
            "metadata_only": "true",
            "notes": notes,
            "claim_boundary": CLAIM_BOUNDARY,
        }
    )


def manual_root_rows(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Load optional manual local-root mappings."""
    manual_path = clean(config.get("manual_local_root_input_path"))
    if path_exists_metadata(manual_path)[0] != "yes":
        return []
    rows: list[dict[str, Any]] = []
    for row in read_csv_rows(manual_path):
        root_key = clean(row.get("root_key"))
        status = clean(row.get("user_status")).lower()
        if status and status not in VALID_USER_STATUS:
            status = "unknown"
        rows.append(
            {
                "root_key": root_key,
                "candidate_path": clean(row.get("local_root_path")),
                "required": clean(row.get("required")).lower() or "unknown",
                "user_status": status or "unknown",
                "notes": clean(row.get("notes")),
            }
        )
    return rows


def scan_text_roots(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Scan prior text/config/output artifacts for local root strings."""
    discovered: dict[str, dict[str, Any]] = {}
    pattern = re.compile(r"(?:C:|c:)[/\\]OpenHeat-local[/\\][^`'\"\s,;)]+")
    output_root = repo_path(config["output_dir"]).resolve()
    for scan_root in config_list(config, "local_root_scan_paths"):
        root = repo_path(scan_root)
        if not root.exists():
            continue
        files = [root] if root.is_file() else root.rglob("*")
        for file_path in files:
            if not file_path.is_file():
                continue
            if output_root in file_path.resolve().parents:
                continue
            if file_path.suffix.lower() not in TEXT_SCAN_SUFFIXES:
                continue
            if is_forbidden_raster_path(file_path):
                continue
            try:
                text = file_path.read_text(encoding="utf-8-sig", errors="ignore")
            except OSError:
                continue
            for match in pattern.findall(text):
                root_path = collapse_to_root(match)
                key = infer_root_key(root_path)
                item = discovered.setdefault(
                    root_path,
                    {
                        "root_key": key,
                        "candidate_path": root_path,
                        "source_count": 0,
                        "source_files": [],
                    },
                )
                item["source_count"] += 1
                source_name = rel_path(file_path)
                if source_name not in item["source_files"] and len(item["source_files"]) < 8:
                    item["source_files"].append(source_name)
    return discovered


def add_prior_inventory_roots(rows: list[dict[str, Any]], config: dict[str, Any]) -> None:
    """Add roots from compact prior root inventories when present."""
    for path_key in ["f2d_root_inventory_path", "f2b_root_candidate_inventory_path"]:
        source_path = clean(config.get(path_key))
        if path_exists_metadata(source_path)[0] != "yes":
            continue
        for row in read_csv_rows(source_path):
            candidate_path = clean(row.get("root_path")) or clean(row.get("root_path_display"))
            if not candidate_path or candidate_path.startswith("<"):
                continue
            add_root_row(
                rows,
                root_key=infer_root_key(candidate_path),
                candidate_path=candidate_path,
                source=path_key,
                source_file=source_path,
                required="no",
                root_kind=clean(row.get("root_kind")) or "prior_root_inventory",
                notes=clean(row.get("notes")),
            )


def selected_root_map(rows: list[dict[str, Any]]) -> dict[str, str]:
    """Return the first usable selected path per root key."""
    selected: dict[str, str] = {}
    priority = {"manual_input": 0, "config_prior_local_root_candidates": 1}
    sorted_rows = sorted(rows, key=lambda row: priority.get(clean(row.get("source")), 10))
    for row in sorted_rows:
        root_key = clean(row.get("root_key"))
        if root_key in selected:
            continue
        if clean(row.get("exists_by_metadata_check")) == "yes" and clean(row.get("user_status")) != "missing":
            selected[root_key] = clean(row.get("candidate_path"))
    return selected


def run(config_path: Path = DEFAULT_CONFIG) -> LocalRootInventoryResult:
    """Run metadata-only local-root inventory."""
    config = load_config(config_path)
    rows: list[dict[str, Any]] = []

    manual_rows = manual_root_rows(config)
    for row in manual_rows:
        add_root_row(
            rows,
            root_key=clean(row["root_key"]),
            candidate_path=clean(row["candidate_path"]),
            source="manual_input",
            source_file=clean(config.get("manual_local_root_input_path")),
            required="yes" if clean(row["required"]).lower() == "yes" else "no",
            user_status=clean(row["user_status"]),
            root_kind="manual_local_root_mapping",
            notes=clean(row["notes"]),
        )

    required_keys = {"b87c_n300_asset_root", "b87c_n300_output_root", "b85_f2c_met_forcing_root", "qgis_manual_check_root"}
    for candidate in config_list(config, "prior_local_root_candidates"):
        add_root_row(
            rows,
            root_key=infer_root_key(candidate),
            candidate_path=candidate,
            source="config_prior_local_root_candidates",
            source_file=rel_path(config_path),
            required="yes" if infer_root_key(candidate) in required_keys else "no",
            root_kind="configured_prior_candidate",
            notes="metadata-only configured candidate; do not create or modify this local root",
        )

    add_prior_inventory_roots(rows, config)
    discovered = scan_text_roots(config)
    source_groups: defaultdict[str, list[str]] = defaultdict(list)
    for item in discovered.values():
        source_groups[item["candidate_path"]].extend(item["source_files"])
    for root_path, item in sorted(discovered.items()):
        add_root_row(
            rows,
            root_key=clean(item["root_key"]),
            candidate_path=root_path,
            source="text_scan_prior_docs_configs_outputs",
            source_file="|".join(item["source_files"]),
            required="no",
            root_kind="discovered_prior_text_root",
            notes=f"source_count={item['source_count']}; metadata-only text scan",
        )

    selected = selected_root_map(rows)
    for row in rows:
        if clean(row.get("root_key")) in selected and clean(row.get("candidate_path")) == selected[clean(row.get("root_key"))]:
            row["selected_for_resolution"] = "yes"

    fieldnames = [
        "root_key",
        "candidate_path",
        "source",
        "source_file",
        "required",
        "user_status",
        "exists_by_metadata_check",
        "is_dir",
        "is_file",
        "parent_exists",
        "size_bytes",
        "selected_for_resolution",
        "root_kind",
        "metadata_only",
        "notes",
        "claim_boundary",
    ]
    write_csv_rows(out_path(config, "b87b1_prior_local_root_inventory.csv"), rows, fieldnames)

    manual_found = bool(manual_rows)
    required_unresolved = [
        key
        for key in required_keys
        if not any(clean(row.get("root_key")) == key and clean(row.get("exists_by_metadata_check")) == "yes" for row in rows)
    ]
    status = "PASS" if not required_unresolved else "WAITING_LOCAL_ROOTS"
    unique_selected_roots = {
        clean(row.get("root_key"))
        for row in rows
        if clean(row.get("selected_for_resolution")) == "yes" and clean(row.get("root_key"))
    }
    return LocalRootInventoryResult(
        status=status,
        rows=len(rows),
        manual_local_roots_found=manual_found,
        roots_resolved_count=len(unique_selected_roots),
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Inventory known prior/candidate local roots by text scan and "
            "Path.exists/is_dir/is_file/stat only. No raster contents are opened."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
