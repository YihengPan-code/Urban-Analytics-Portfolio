"""Build the B8.7b compact N300 sample index.

Inputs:
    configs/v12/systemb_b87b_n300_execution_precheck.yaml, the B8.6g3 N300 v4
    design, N150 selected-cell inventory, and F5 pairwise labels.
Outputs:
    b87b_n300_total_sample_index.csv, b87b_new_candidate_sample_index.csv, and
    b87b_existing_n150_label_inventory.csv.
Saved metrics:
    Existing labelled N150 cell count, new candidate count, total unique N300
    cell count, per-cell label multiplicity, source lane, role/typology fields,
    source-review caveats, execution-precheck status, and claim boundary. This
    script creates no SOLWEIG execution manifest and no run-ready artifacts.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from v12_b87b_input_inventory import CLAIM_BOUNDARY, DEFAULT_CONFIG, clean
from v12_b87b_input_inventory import load_config, out_path, read_csv_rows, write_csv_rows


@dataclass(frozen=True)
class SampleIndexResult:
    """B8.7b sample-index result."""

    status: str
    existing_n150_count: int
    new_candidate_count: int
    total_unique_cell_count: int
    overlap_count: int


SAMPLE_FIELDNAMES = [
    "cell_id",
    "sample_group",
    "source_lane",
    "primary_role",
    "spatial_bin",
    "typology",
    "source_closeout_status",
    "caveat_flags",
    "execution_precheck_status",
    "claim_boundary",
]


def selected_cell_lookup(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    """Return N150 selected-cell rows by cell ID."""
    return {clean(row.get("cell_id")): row for row in rows if clean(row.get("cell_id"))}


def f5_label_inventory(
    pairwise_rows: list[dict[str, str]],
    selected_lookup: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    """Summarize existing N150 labelled-cell inventory."""
    by_cell: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in pairwise_rows:
        cell_id = clean(row.get("cell_id"))
        if cell_id:
            by_cell[cell_id].append(row)
    inventory: list[dict[str, Any]] = []
    for cell_id in sorted(by_cell):
        rows = by_cell[cell_id]
        forcing_days = sorted({clean(row.get("forcing_day_id")) for row in rows if clean(row.get("forcing_day_id"))})
        hours = sorted({clean(row.get("hour_sgt")) for row in rows if clean(row.get("hour_sgt"))}, key=lambda x: int(x))
        selected = selected_lookup.get(cell_id, {})
        expected_rows = len(forcing_days) * len(hours)
        status = "PASS" if len(rows) == expected_rows and len(rows) == 10 else "WARN"
        inventory.append(
            {
                "cell_id": cell_id,
                "sample_group": "existing_n150_labelled",
                "label_rows": len(rows),
                "forcing_day_count": len(forcing_days),
                "hour_count": len(hours),
                "forcing_day_ids": "|".join(forcing_days),
                "hours_sgt": "|".join(hours),
                "source_lane": "B8.5-F5 N150 multi-forcing labelled set",
                "selection_status": clean(selected.get("selection_status")),
                "primary_role": clean(selected.get("primary_sampling_stratum")) or "existing_n150_labelled",
                "typology": clean(selected.get("typology_label")) or "not_recorded",
                "pairwise_label_status": status,
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    return inventory


def existing_sample_rows(inventory: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert existing-label inventory to the shared sample-index shape."""
    rows: list[dict[str, Any]] = []
    for item in inventory:
        caveat_flags = clean(item.get("selection_status"))
        rows.append(
            {
                "cell_id": item["cell_id"],
                "sample_group": "existing_n150_labelled",
                "source_lane": "B8.5-F5 labelled N150",
                "primary_role": item["primary_role"],
                "spatial_bin": "not_recorded_in_n150_selected_cells",
                "typology": item["typology"],
                "source_closeout_status": "not_applicable_existing_labelled_set",
                "caveat_flags": caveat_flags,
                "execution_precheck_status": "existing_f5_label_present_no_new_b87b_execution",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    return rows


def new_candidate_rows(design_rows: list[dict[str, str]], existing_cells: set[str]) -> list[dict[str, Any]]:
    """Convert B8.6g3 v4 design rows to sample-index rows."""
    rows: list[dict[str, Any]] = []
    for item in design_rows:
        closeout = clean(item.get("source_closeout_status")) or "NOT_REVIEW_REQUIRED"
        caveat = clean(item.get("source_closeout_caveat"))
        cell_id = clean(item.get("cell_id"))
        status = "pending_new_n150_execution_precheck"
        if cell_id in existing_cells:
            status = "BLOCKED_OVERLAPS_EXISTING_N150"
        caveat_flags = closeout if closeout != "NOT_REVIEW_REQUIRED" else ""
        if caveat:
            caveat_flags = f"{caveat_flags}|caveat_documented" if caveat_flags else "caveat_documented"
        rows.append(
            {
                "cell_id": cell_id,
                "sample_group": "new_n150_candidate",
                "source_lane": "B8.6g3 N300 v4 source-reviewed design",
                "primary_role": clean(item.get("primary_role")),
                "spatial_bin": clean(item.get("spatial_bin")),
                "typology": clean(item.get("typology")),
                "source_closeout_status": closeout,
                "caveat_flags": caveat_flags,
                "execution_precheck_status": status,
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    return rows


def run(config_path: Path = DEFAULT_CONFIG) -> SampleIndexResult:
    """Create B8.7b compact sample-index outputs."""
    config = load_config(config_path)
    design = read_csv_rows(config["b86g3_n300_v4_design_path"])
    selected = read_csv_rows(config["n150_selected_cells_path"])
    f5_labels = read_csv_rows(config["f5_pairwise_label_path"])
    selected_lookup = selected_cell_lookup(selected)
    existing_inventory = f5_label_inventory(f5_labels, selected_lookup)
    existing_cells = {clean(row["cell_id"]) for row in existing_inventory}
    new_rows = new_candidate_rows(design, existing_cells)
    existing_rows = existing_sample_rows(existing_inventory)
    total_rows = existing_rows + new_rows
    unique_count = len({clean(row["cell_id"]) for row in total_rows if clean(row["cell_id"])})
    overlap_count = len({clean(row["cell_id"]) for row in new_rows}.intersection(existing_cells))

    write_csv_rows(
        out_path(config, "b87b_existing_n150_label_inventory.csv"),
        existing_inventory,
        [
            "cell_id",
            "sample_group",
            "label_rows",
            "forcing_day_count",
            "hour_count",
            "forcing_day_ids",
            "hours_sgt",
            "source_lane",
            "selection_status",
            "primary_role",
            "typology",
            "pairwise_label_status",
            "claim_boundary",
        ],
    )
    write_csv_rows(out_path(config, "b87b_new_candidate_sample_index.csv"), new_rows, SAMPLE_FIELDNAMES)
    write_csv_rows(out_path(config, "b87b_n300_total_sample_index.csv"), total_rows, SAMPLE_FIELDNAMES)

    expected_existing = int(config["expected_existing_n150_count"])
    expected_new = int(config["expected_new_candidate_count"])
    expected_total = int(config["expected_total_n300_count"])
    status = (
        "PASS"
        if len(existing_inventory) == expected_existing
        and len(new_rows) == expected_new
        and unique_count == expected_total
        and overlap_count == 0
        else "BLOCKED"
    )
    return SampleIndexResult(
        status=status,
        existing_n150_count=len(existing_inventory),
        new_candidate_count=len(new_rows),
        total_unique_cell_count=unique_count,
        overlap_count=overlap_count,
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Build the compact B8.7b N300 sample index from existing N150 labels "
            "and new B8.6g3 candidates. This is not a SOLWEIG run manifest."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
