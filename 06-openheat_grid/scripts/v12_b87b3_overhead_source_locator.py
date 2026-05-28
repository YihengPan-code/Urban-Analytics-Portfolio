"""Locate the overhead structure source from v12 source references.

Inputs:
    b87b3_manual_source_ingest.csv, especially rows with
    source_kind=asset_inventory, plus expected_overhead_source_path from the
    B8.7b.3 config.
Outputs:
    b87b3_overhead_source_inventory.csv.
Saved metrics:
    Source-reference path, matched config key/text pattern, overhead source
    path, existence by metadata, version status, and whether the source can
    support the overhead_as_canopy scenario. The script reads compact JSON/MD
    source notes only; it does not run QGIS/SOLWEIG or open/write rasters.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from v12_b87b3_input_inventory import (
    CLAIM_BOUNDARY,
    DEFAULT_CONFIG,
    clean,
    load_config,
    metadata_for_path,
    normalized_abs,
    out_path,
    path_exists_text,
    read_csv_rows,
    repo_path,
    write_csv_rows,
)


def find_json_overhead_paths(data: Any, prefix: str = "") -> list[tuple[str, str]]:
    """Recursively find overhead GeoJSON paths in JSON-like data."""
    matches: list[tuple[str, str]] = []
    if isinstance(data, dict):
        for key, value in data.items():
            key_path = f"{prefix}.{key}" if prefix else clean(key)
            lowered = clean(key).lower()
            if isinstance(value, str) and "overhead" in (lowered + value.lower()) and value.lower().endswith(".geojson"):
                matches.append((key_path, value))
            matches.extend(find_json_overhead_paths(value, key_path))
    elif isinstance(data, list):
        for index, value in enumerate(data):
            matches.extend(find_json_overhead_paths(value, f"{prefix}[{index}]"))
    return matches


def source_reference_rows(config: dict[str, Any]) -> list[dict[str, str]]:
    """Load asset-inventory rows from manual ingestion."""
    try:
        rows = read_csv_rows(out_path(config, "b87b3_manual_source_ingest.csv"))
    except FileNotFoundError:
        rows = read_csv_rows(config["manual_source_csv_path"])
    return [
        row
        for row in rows
        if clean(row.get("source_kind")) == "asset_inventory"
        and clean(row.get("user_decision")) == "use"
        and clean(row.get("absolute_path"))
    ]


def inspect_reference(config: dict[str, Any], reference_path: str) -> list[dict[str, Any]]:
    """Inspect one compact source-reference file for overhead source paths."""
    resolved = repo_path(reference_path)
    if not resolved.exists() or not resolved.is_file():
        return []
    try:
        text = resolved.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return []
    matches: list[tuple[str, str]] = []
    if resolved.suffix.lower() == ".json":
        try:
            matches.extend(find_json_overhead_paths(json.loads(text)))
        except json.JSONDecodeError:
            pass
    for match in re.finditer(r"data[/\\]features_3d[/\\]v10[/\\]overhead[/\\][A-Za-z0-9_.-]+\.geojson", text):
        matches.append(("text_pattern:data/features_3d/v10/overhead/*.geojson", match.group(0)))
    rows: list[dict[str, Any]] = []
    for match_key, raw_path in matches:
        overhead_path = normalized_abs(raw_path, config["main_worktree_root"])
        exists = path_exists_text(overhead_path)
        expected = clean(config["expected_overhead_source_path"]).replace("\\", "/").lower()
        observed = overhead_path.replace("\\", "/").lower()
        version_status = "LOCKED_CANONICAL_V10_OVERHEAD_LAYER" if observed == expected and exists == "yes" else "CANDIDATE_REVIEW"
        if exists != "yes":
            version_status = "OVERHEAD_SOURCE_MISSING"
        rows.append(
            {
                "source_reference_path": reference_path,
                "match_key": match_key,
                "overhead_source_path": overhead_path,
                "exists_by_metadata": exists,
                "version_status": version_status,
                "supports_overhead_scenario": "yes" if exists == "yes" else "no",
                "notes": "Recovered from v12 config/source note; vector metadata only.",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    return rows


def expected_overhead_row(config: dict[str, Any]) -> dict[str, Any]:
    """Return an explicit expected-path cross-check row."""
    path = clean(config["expected_overhead_source_path"])
    exists = path_exists_text(path)
    return {
        "source_reference_path": "config.expected_overhead_source_path",
        "match_key": "expected_overhead_source_path",
        "overhead_source_path": path,
        "exists_by_metadata": exists,
        "version_status": "LOCKED_CANONICAL_V10_OVERHEAD_LAYER" if exists == "yes" else "OVERHEAD_SOURCE_MISSING",
        "supports_overhead_scenario": "yes" if exists == "yes" else "no",
        "notes": "Expected v10 overhead layer from recovered context.",
        "claim_boundary": CLAIM_BOUNDARY,
    }


def run(config_path: Path = DEFAULT_CONFIG) -> list[dict[str, Any]]:
    """Run overhead source location."""
    config = load_config(config_path)
    rows = [expected_overhead_row(config)]
    for reference in source_reference_rows(config):
        rows.extend(inspect_reference(config, clean(reference.get("absolute_path"))))
    unique: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        unique[(clean(row["source_reference_path"]), clean(row["overhead_source_path"]))] = row
    result = list(unique.values())
    if not any(clean(row["exists_by_metadata"]) == "yes" for row in result):
        result.append(
            {
                "source_reference_path": "",
                "match_key": "OVERHEAD_SOURCE_MISSING",
                "overhead_source_path": "",
                "exists_by_metadata": "no",
                "version_status": "OVERHEAD_SOURCE_MISSING",
                "supports_overhead_scenario": "no",
                "notes": "No overhead_structures_geojson or overhead canopy vector source recovered.",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    write_csv_rows(
        out_path(config, "b87b3_overhead_source_inventory.csv"),
        result,
        [
            "source_reference_path",
            "match_key",
            "overhead_source_path",
            "exists_by_metadata",
            "version_status",
            "supports_overhead_scenario",
            "notes",
            "claim_boundary",
        ],
    )
    return result


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Parse v12 configs/source notes for overhead_structures_geojson and "
            "write b87b3_overhead_source_inventory.csv; metadata only."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(f"overhead_source_rows={len(run(args.config))}")


if __name__ == "__main__":
    main()
