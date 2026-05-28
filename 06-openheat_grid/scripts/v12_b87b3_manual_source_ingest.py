"""Ingest manually recovered full-raster source decisions.

Inputs:
    manual_source_csv_path from
    configs/v12/systemb_b87b3_full_raster_source_preplan.yaml.
Outputs:
    b87b3_manual_source_ingest.csv.
Saved metrics:
    Manual source kind, scenario, absolute path, user decision, version status,
    path existence by metadata, source role, and asset-inventory flag. The
    script reads only compact CSV/text metadata and does not open raster pixels,
    svfs.zip, QGIS, or SOLWEIG.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from v12_b87b3_input_inventory import (
    CLAIM_BOUNDARY,
    DEFAULT_CONFIG,
    clean,
    load_config,
    metadata_for_path,
    out_path,
    read_csv_rows,
    write_csv_rows,
)


def source_role(source_kind: str, user_decision: str) -> str:
    """Classify a manual source decision."""
    if user_decision == "use" and source_kind == "asset_inventory":
        return "source_reference_to_parse"
    if user_decision == "use":
        return "candidate_canonical_source"
    if user_decision.startswith("not_applicable"):
        return "not_applicable"
    if user_decision in {"reject", "missing"}:
        return user_decision
    return "manual_review"


def run(config_path: Path = DEFAULT_CONFIG) -> list[dict[str, Any]]:
    """Run manual source ingestion."""
    config = load_config(config_path)
    manual_rows = read_csv_rows(config["manual_source_csv_path"])
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(manual_rows, start=1):
        source_kind = clean(row.get("source_kind"))
        path = clean(row.get("absolute_path"))
        meta = metadata_for_path(path) if path else {
            "exists_by_metadata": "not_applicable",
            "is_file": "not_applicable",
            "is_dir": "not_applicable",
            "size_bytes": "",
            "metadata_error": "",
        }
        rows.append(
            {
                "manual_row_id": index,
                "source_kind": source_kind,
                "scenario": clean(row.get("scenario")),
                "absolute_path": path,
                "user_decision": clean(row.get("user_decision")),
                "version_status": clean(row.get("version_status")),
                "exists_by_metadata": meta["exists_by_metadata"],
                "is_file": meta["is_file"],
                "size_bytes": meta["size_bytes"],
                "source_role": source_role(source_kind, clean(row.get("user_decision"))),
                "notes": clean(row.get("notes")),
                "metadata_only": "true",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    write_csv_rows(
        out_path(config, "b87b3_manual_source_ingest.csv"),
        rows,
        [
            "manual_row_id",
            "source_kind",
            "scenario",
            "absolute_path",
            "user_decision",
            "version_status",
            "exists_by_metadata",
            "is_file",
            "size_bytes",
            "source_role",
            "notes",
            "metadata_only",
            "claim_boundary",
        ],
    )
    return rows


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Ingest the B8.7b.3 manual full-raster source CSV and write "
            "b87b3_manual_source_ingest.csv; metadata only."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(f"manual_source_rows={len(run(args.config))}")


if __name__ == "__main__":
    main()
