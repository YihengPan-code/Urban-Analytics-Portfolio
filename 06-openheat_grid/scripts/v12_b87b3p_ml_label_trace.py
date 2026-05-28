"""Trace current ML labels to their SOLWEIG source batch for B8.7b.3p.

Inputs:
    outputs/v12_surrogate/b8_5_f5_n150_multiforcing/
    b85_f5_pairwise_delta_by_cell_hour.csv plus B8.6b label inventory and
    surrogate dataset evidence when present.
Outputs:
    b87b3p_ml_label_trace_matrix.csv.
Saved metrics:
    Label row count, unique cell count, forcing days, hours, source batch,
    protocol ID/status, source columns, and mixed-protocol risk. This script
    reads compact CSV labels only; it does not run QGIS/SOLWEIG, read raster
    pixels, open svfs.zip, create a manifest/runner, stage, or commit.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from v12_b87b3p_input_inventory import (
    CLAIM_BOUNDARY,
    DEFAULT_CONFIG,
    clean,
    load_config,
    out_path,
    read_csv_rows,
    repo_path,
    unique_values,
    write_csv_rows,
)


TRACE_FIELDS = [
    "label_file",
    "row_count",
    "unique_cells",
    "forcing_day_set",
    "hour_sgt_set",
    "source_batch",
    "protocol_id",
    "protocol_status",
    "label_source_values",
    "legacy_single_forcing_comparison_source_values",
    "evidence",
    "mismatch_risk",
    "notes",
    "claim_boundary",
]


def label_summary(path: str) -> dict[str, Any]:
    """Summarize a compact label CSV."""
    resolved = repo_path(path)
    if not resolved.exists():
        return {
            "row_count": "0",
            "unique_cells": "0",
            "forcing_day_set": "",
            "hour_sgt_set": "",
            "label_source_values": "",
            "legacy_single_forcing_comparison_source_values": "",
            "read_status": "MISSING",
        }
    rows = read_csv_rows(resolved)
    return {
        "row_count": clean(len(rows)),
        "unique_cells": clean(len(unique_values(rows, "cell_id"))),
        "forcing_day_set": "|".join(unique_values(rows, "forcing_day_id")),
        "hour_sgt_set": "|".join(unique_values(rows, "hour_sgt")),
        "label_source_values": "|".join(unique_values(rows, "label_source")),
        "legacy_single_forcing_comparison_source_values": "|".join(unique_values(rows, "legacy_single_forcing_comparison_source")),
        "read_status": "READ_OK",
    }


def infer_protocol_status(summary: dict[str, Any]) -> tuple[str, str, str]:
    """Infer label protocol status and mixed-protocol risk."""
    label_sources = [item for item in clean(summary.get("label_source_values", "")).split("|") if item]
    legacy_values = [item for item in clean(summary.get("legacy_single_forcing_comparison_source_values", "")).split("|") if item]
    if clean(summary.get("read_status")) != "READ_OK":
        return "UNKNOWN_REQUIRES_REVIEW", "HIGH", "Label file missing or unreadable."
    if len(label_sources) > 1:
        return "FAIL_PROTOCOL_MIXING_IN_ML_LABELS", "HIGH", "Multiple label_source values found in current ML label table."
    if legacy_values and any(value != "metadata_only_not_merged" for value in legacy_values):
        return "UNKNOWN_REQUIRES_REVIEW", "MEDIUM", "Legacy single-forcing source column is not explicitly metadata-only."
    expected_shape = clean(summary.get("row_count")) == "1500" and clean(summary.get("unique_cells")) == "150"
    if expected_shape and label_sources == ["b85_f5_n150_multiforcing_raster_qa"]:
        return "PASS_SINGLE_F5_PROTOCOL", "LOW", "F5 label file has one label source and legacy single-forcing is metadata-only."
    return "UNKNOWN_REQUIRES_REVIEW", "MEDIUM", "Label table exists but shape/source did not match the expected F5 signature."


def run(config_path: str | Path = DEFAULT_CONFIG) -> list[dict[str, Any]]:
    """Run ML label source trace."""
    config = load_config(config_path)
    inputs = config.get("inputs", {})
    label_path = clean(inputs.get("f5_pairwise_label", ""))
    summary = label_summary(label_path)
    status, risk, note = infer_protocol_status(summary)
    evidence = ";".join(
        clean(path)
        for path in [
            label_path,
            inputs.get("f5_manifest", ""),
            inputs.get("f5_label_merge_plan", ""),
            inputs.get("f5_status", ""),
            inputs.get("b86b_label_source_inventory", ""),
            inputs.get("b86b_surrogate_dataset", ""),
        ]
        if clean(path)
    )
    rows = [
        {
            "label_file": label_path,
            "row_count": summary["row_count"],
            "unique_cells": summary["unique_cells"],
            "forcing_day_set": summary["forcing_day_set"],
            "hour_sgt_set": summary["hour_sgt_set"],
            "source_batch": "b85_f5_n150_multiforcing",
            "protocol_id": clean(config.get("final_n150_protocol_id", "F5_N150_PROTOCOL")),
            "protocol_status": status,
            "label_source_values": summary["label_source_values"],
            "legacy_single_forcing_comparison_source_values": summary["legacy_single_forcing_comparison_source_values"],
            "evidence": evidence,
            "mismatch_risk": risk,
            "notes": note,
            "claim_boundary": CLAIM_BOUNDARY,
        }
    ]
    write_csv_rows(out_path(config, "b87b3p_ml_label_trace_matrix.csv"), rows, TRACE_FIELDS)
    return rows


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Trace the current System B ML label CSV to its SOLWEIG source "
            "batch. Reads compact labels only; no QGIS/SOLWEIG or raster/svfs.zip "
            "content access."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    rows = run(args.config)
    print(f"ml_label_trace_rows={len(rows)}")
    print(f"protocol_status={rows[0]['protocol_status']}")


if __name__ == "__main__":
    main()
