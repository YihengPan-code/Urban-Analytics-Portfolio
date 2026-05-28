"""Validate the B8.6g3 N300 v4 source-reviewed design for B8.7b.

Inputs:
    configs/v12/systemb_b87b_n300_execution_precheck.yaml,
    b86g3_n300_v4_design_path, b86g3_closeout_path, f5_pairwise_label_path,
    b87a_patched_design_path, and b87_design_freeze_candidates_path.
Outputs:
    outputs/v12_surrogate/b8_7b_n300_execution_precheck/
    b87b_n300_v4_design_validation.csv.
Saved metrics:
    New candidate count, duplicate cell count, N150 overlap count, source-review
    caveat carry-through, excluded water-cell absence, role preservation, and
    required-column checks. This is design validation only; it does not create
    execution artifacts, read rasters, run QGIS/SOLWEIG, or produce AOI/B9/WBGT/
    hazard/risk/System A-B coupling outputs.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from v12_b87b_input_inventory import CLAIM_BOUNDARY, DEFAULT_CONFIG, clean
from v12_b87b_input_inventory import config_list, load_config, out_path, read_csv_rows, write_csv_rows


@dataclass(frozen=True)
class DesignValidationResult:
    """B8.7b design validation result."""

    status: str
    candidate_count: int
    duplicate_count: int
    n150_overlap_count: int
    failed_checks: int
    warning_checks: int


REQUIRED_DESIGN_COLUMNS = [
    "cell_id",
    "primary_role",
    "secondary_roles",
    "spatial_bin",
    "typology",
    "source_closeout_status",
    "source_closeout_caveat",
    "execution_precheck_blocker",
    "claim_boundary",
]


def row_status(ok: bool, warn: bool = False) -> str:
    """Return PASS/WARN/FAIL for one validation row."""
    if ok:
        return "WARN" if warn else "PASS"
    return "FAIL"


def cell_set(rows: list[dict[str, str]]) -> set[str]:
    """Return non-empty cell IDs from rows."""
    return {clean(row.get("cell_id")) for row in rows if clean(row.get("cell_id"))}


def role_counter(rows: list[dict[str, str]]) -> Counter[str]:
    """Count primary roles."""
    return Counter(clean(row.get("primary_role")) for row in rows if clean(row.get("primary_role")))


def role_pairs(rows: list[dict[str, str]]) -> dict[str, tuple[str, str]]:
    """Return cell role metadata keyed by cell."""
    return {
        clean(row.get("cell_id")): (clean(row.get("primary_role")), clean(row.get("secondary_roles")))
        for row in rows
        if clean(row.get("cell_id"))
    }


def add_row(rows: list[dict[str, Any]], item: str, status: str, evidence: str, detail: str = "") -> None:
    """Append one design validation row."""
    rows.append(
        {
            "validation_item": item,
            "status": status,
            "evidence": evidence,
            "detail": detail,
            "claim_boundary": CLAIM_BOUNDARY,
        }
    )


def run(config_path: Path = DEFAULT_CONFIG) -> DesignValidationResult:
    """Validate the N300 v4 design."""
    config = load_config(config_path)
    design = read_csv_rows(config["b86g3_n300_v4_design_path"])
    f5_labels = read_csv_rows(config["f5_pairwise_label_path"])
    n150_cells = cell_set(f5_labels)
    expected_new = int(config["expected_new_candidate_count"])
    candidate_cells = [clean(row.get("cell_id")) for row in design]
    duplicate_count = len(candidate_cells) - len(set(candidate_cells))
    overlap = sorted(set(candidate_cells).intersection(n150_cells))
    rows: list[dict[str, Any]] = []

    add_row(
        rows,
        "n300_v4_candidate_count",
        row_status(len(design) == expected_new),
        f"rows={len(design)} expected={expected_new}",
    )
    add_row(
        rows,
        "duplicate_new_candidate_cell_id",
        row_status(duplicate_count == 0),
        f"duplicate_count={duplicate_count}",
    )
    add_row(
        rows,
        "n150_overlap",
        row_status(len(overlap) == 0),
        f"overlap_count={len(overlap)}",
        "|".join(overlap),
    )

    columns = set(design[0].keys()) if design else set()
    missing_columns = [column for column in REQUIRED_DESIGN_COLUMNS if column not in columns]
    add_row(
        rows,
        "required_columns_present",
        row_status(not missing_columns),
        "missing=" + ("none" if not missing_columns else "|".join(missing_columns)),
    )

    blocked_rows = [
        clean(row.get("cell_id"))
        for row in design
        if clean(row.get("execution_precheck_blocker")).lower() not in {"", "no", "false", "0"}
    ]
    add_row(
        rows,
        "execution_precheck_blocker_flags",
        row_status(not blocked_rows),
        f"blocked_rows={len(blocked_rows)}",
        "|".join(blocked_rows),
    )

    caveat_cells = config_list(config, "source_review_caveat_cells")
    design_by_cell = {clean(row.get("cell_id")): row for row in design}
    closeout = {clean(row.get("source_review_cell")): row for row in read_csv_rows(config["b86g3_closeout_path"])}
    for cell_id in caveat_cells:
        design_row = design_by_cell.get(cell_id)
        closeout_row = closeout.get(cell_id)
        status = "FAIL"
        evidence = "missing_from_design"
        detail = ""
        if design_row:
            closeout_status = clean(design_row.get("source_closeout_status"))
            blocker = clean(design_row.get("execution_precheck_blocker")).lower()
            caveat = clean(design_row.get("source_closeout_caveat"))
            closeout_expected = clean(closeout_row.get("source_closeout_status")) if closeout_row else ""
            ok = bool(closeout_status and closeout_status != "NOT_REVIEW_REQUIRED" and blocker in {"no", "false", "0"})
            status = row_status(ok)
            evidence = (
                f"design_status={closeout_status}; closeout_status={closeout_expected}; "
                f"execution_precheck_blocker={blocker or 'blank'}"
            )
            detail = caveat
        add_row(rows, f"caveat_carried_{cell_id}", status, evidence, detail)

    for cell_id in config_list(config, "excluded_water_cells"):
        present = cell_id in design_by_cell
        add_row(
            rows,
            f"excluded_water_cell_absent_{cell_id}",
            row_status(not present),
            "present_in_v4_design=" + yes_no_local(present),
        )

    b87a_path = clean(config.get("b87a_patched_design_path"))
    if b87a_path and Path(b87a_path).suffix.lower() == ".csv":
        b87a_rows = read_csv_rows(b87a_path)
        current_roles = role_pairs(design)
        prior_roles = role_pairs(b87a_rows)
        changed = [
            cell
            for cell, roles in current_roles.items()
            if cell in prior_roles and roles != prior_roles[cell]
        ]
        add_row(
            rows,
            "candidate_roles_preserved_vs_b87a",
            row_status(not changed),
            f"changed_role_cells={len(changed)}",
            "|".join(changed),
        )
        add_row(
            rows,
            "role_quota_preserved_vs_b87a",
            row_status(role_counter(design) == role_counter(b87a_rows)),
            f"current={dict(role_counter(design))}; b87a={dict(role_counter(b87a_rows))}",
        )

    b87_path = clean(config.get("b87_design_freeze_candidates_path"))
    if b87_path and Path(b87_path).suffix.lower() == ".csv":
        b87_rows = read_csv_rows(b87_path)
        add_row(
            rows,
            "role_quota_preserved_vs_b87",
            row_status(role_counter(design) == role_counter(b87_rows)),
            f"current={dict(role_counter(design))}; b87={dict(role_counter(b87_rows))}",
        )

    fieldnames = ["validation_item", "status", "evidence", "detail", "claim_boundary"]
    write_csv_rows(out_path(config, "b87b_n300_v4_design_validation.csv"), rows, fieldnames)
    failed = sum(1 for row in rows if row["status"] == "FAIL")
    warnings = sum(1 for row in rows if row["status"] == "WARN")
    status = "PASS" if failed == 0 else "BLOCKED"
    return DesignValidationResult(
        status=status,
        candidate_count=len(design),
        duplicate_count=duplicate_count,
        n150_overlap_count=len(overlap),
        failed_checks=failed,
        warning_checks=warnings,
    )


def yes_no_local(value: bool) -> str:
    """Small local yes/no formatter to keep validation rows readable."""
    return "yes" if value else "no"


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Validate B8.6g3 N300 v4 source-reviewed design for B8.7b. "
            "Writes compact CSV validation only; no raster/QGIS/SOLWEIG/run-ready "
            "manifest/local runner/AOI/B9/WBGT/hazard/risk output is created."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
