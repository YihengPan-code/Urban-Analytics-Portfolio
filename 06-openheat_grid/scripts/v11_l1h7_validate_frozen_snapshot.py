#!/usr/bin/env python
"""Validate a System A A-L1H.7 frozen snapshot table.

Inputs:
    - configs/v11/systema_l1h7_formal_snapshot_freezer.yaml
    - A frozen compact CSV, CSV.GZ, or Parquet snapshot supplied with
      --snapshot, or the frozen_table_path recorded in the A-L1H.7 manifest.

Outputs:
    - outputs/v11_systema_l1_high_tail/formal_snapshot_freezer/
      a_l1h7_frozen_snapshot_validation.csv

Saved metrics:
    - Required-schema status, forbidden-column status, prospective row count,
      ge31/ge33 support, numeric checks, model/version metadata checks,
      quality-flag checks, and retrospective/prospective label checks.

This validator does not train models, change A-L1H.5 contract decisions, change
A-L1H.6 promotion gates, modify archive collectors, create station-adjusted
WBGT, create local 100 m WBGT, create risk/hazard scores, or fabricate rows.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import v11_l1h7_formal_snapshot_freezer as freezer


def snapshot_from_manifest(config: dict[str, object]) -> Path | None:
    """Return the frozen snapshot path from the manifest, if present."""
    outputs = freezer.output_paths_from_config(config)
    manifest_path = outputs["frozen_snapshot_manifest"]
    rows = freezer.read_csv_rows(manifest_path)
    if not rows:
        return None
    raw_path = rows[0].get("frozen_table_path", "")
    if not raw_path:
        return None
    return freezer.resolve_path(raw_path)


def validate_snapshot(config_path: Path, snapshot_path: Path | None) -> int:
    """Validate one frozen snapshot and refresh validation CSV output."""
    config = freezer.load_config(config_path)
    if snapshot_path is None:
        snapshot_path = snapshot_from_manifest(config)
    outputs = freezer.output_paths_from_config(config)
    if snapshot_path is None:
        freezer.write_csv(
            outputs["frozen_snapshot_validation"],
            [
                {
                    "validation_target": "",
                    "check_id": "frozen_snapshot_path_available",
                    "check_group": "availability",
                    "check_status": "WAITING",
                    "detail": "No --snapshot path supplied and manifest has no frozen_table_path.",
                }
            ],
            ["validation_target", "check_id", "check_group", "check_status", "detail"],
        )
        print("[validation_status] WAITING")
        print("[snapshot_path] none")
        return 1
    if not snapshot_path.exists():
        freezer.write_csv(
            outputs["frozen_snapshot_validation"],
            [
                {
                    "validation_target": freezer.rel(snapshot_path),
                    "check_id": "frozen_snapshot_exists",
                    "check_group": "availability",
                    "check_status": "FAIL",
                    "detail": "Snapshot path does not exist.",
                }
            ],
            ["validation_target", "check_id", "check_group", "check_status", "detail"],
        )
        print("[validation_status] FAIL")
        print(f"[snapshot_path] {freezer.rel(snapshot_path)}")
        return 1

    required, optional, forbidden = freezer.load_schema_contract(config)
    preview = freezer.read_table_preview(snapshot_path, config)
    assessment = freezer.assess_candidate(preview, required, optional, forbidden, config)
    validation_status = "PASS" if assessment.readiness_status == "READY_TO_FREEZE" else assessment.readiness_status
    rows = [
        {
            "validation_target": freezer.rel(snapshot_path),
            "check_id": row["check_id"],
            "check_group": row["check_group"],
            "check_status": row["check_status"],
            "detail": row["detail"],
        }
        for row in assessment.check_rows
    ]
    rows.append(
        {
            "validation_target": freezer.rel(snapshot_path),
            "check_id": "standalone_validation_decision",
            "check_group": "decision",
            "check_status": validation_status,
            "detail": assessment.readiness_reason,
        }
    )
    freezer.write_csv(
        outputs["frozen_snapshot_validation"],
        rows,
        ["validation_target", "check_id", "check_group", "check_status", "detail"],
    )
    print(f"[validation_status] {validation_status}")
    print(f"[snapshot_path] {freezer.rel(snapshot_path)}")
    print(f"[n_rows] {assessment.n_rows}")
    print(f"[n_prospective_rows] {assessment.n_prospective_rows}")
    print(f"[n_ge31] {assessment.n_ge31}")
    print(f"[n_ge33] {assessment.n_ge33}")
    return 0 if validation_status == "PASS" else 1


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description=(
            "Validate an A-L1H.7 frozen snapshot against the A-L1H.6 required "
            "schema, forbidden-column guard, numeric checks, metadata checks, "
            "quality/provenance label checks, and prospective support thresholds."
        )
    )
    parser.add_argument("--config", default="configs/v11/systema_l1h7_formal_snapshot_freezer.yaml", help="Path to the explicit A-L1H.7 YAML config.")
    parser.add_argument("--snapshot", default="", help="Optional compact snapshot path. If omitted, use frozen_table_path from the manifest.")
    args = parser.parse_args()
    snapshot = freezer.resolve_path(args.snapshot) if args.snapshot else None
    return validate_snapshot(freezer.resolve_path(args.config), snapshot)


if __name__ == "__main__":
    raise SystemExit(main())
