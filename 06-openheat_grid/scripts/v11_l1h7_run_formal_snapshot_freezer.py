#!/usr/bin/env python
"""Run the System A A-L1H.7 formal snapshot freezer.

Inputs:
    - configs/v11/systema_l1h7_formal_snapshot_freezer.yaml
    - A-L1H.5 output schema.
    - A-L1H.6 expected input schema and status.
    - Compact candidate tables under configured formal/prospective roots.

Outputs:
    - a_l1h7_input_inventory.csv
    - a_l1h7_candidate_table_inventory.csv
    - a_l1h7_column_mapping_candidates.csv
    - a_l1h7_required_schema_check.csv
    - a_l1h7_forbidden_column_check.csv
    - a_l1h7_freeze_readiness_check.csv
    - a_l1h7_snapshot_manifest_schema.csv
    - a_l1h7_snapshot_command_template.md
    - a_l1h7_downstream_l1h6_rerun_instructions.md
    - a_l1h7_frozen_snapshot_manifest.csv
    - a_l1h7_frozen_snapshot_validation.csv
    - a_l1h7_report.md
    - A_L1H7_STATUS.md
    - docs/v11/OpenHeat_SystemA_L1H7_formal_snapshot_freezer_CN.md

Saved metrics:
    - Candidate count, best candidate path, freeze mode, row/event support,
      schema status, forbidden-column status, checksums, and downstream
      A-L1H.6 rerun command. In dry_run mode no snapshot data table is written.

This runner does not stage, commit, train models, touch archive collectors,
touch System B/SOLWEIG outputs, create station-adjusted WBGT, create local
100 m WBGT, create risk/hazard scores, promote P_ge31 to an official warning
probability, or fabricate prospective rows.
"""
from __future__ import annotations

import argparse
import traceback
from datetime import datetime
from pathlib import Path

import v11_l1h7_formal_snapshot_freezer as freezer


def fallback_outputs() -> dict[str, Path]:
    """Return output paths used when config loading itself fails."""
    base = freezer.resolve_path("outputs/v11_systema_l1_high_tail/formal_snapshot_freezer")
    return {
        "report": base / "a_l1h7_report.md",
        "status": base / "A_L1H7_STATUS.md",
    }


def write_failure_outputs(config_path: str, error_text: str) -> None:
    """Best-effort FAILED status writer for unexpected script errors."""
    try:
        config = freezer.load_config(freezer.resolve_path(config_path))
        outputs = freezer.output_paths_from_config(config)
    except Exception:
        outputs = fallback_outputs()
    today = datetime.now().date().isoformat()
    report = f"""# System A A-L1H.7 Formal Snapshot Freezer

Generated: {today}
Decision status: `FAILED`

The freezer encountered an unexpected script error before completing outputs.

```text
{error_text}
```
"""
    status = f"""# A-L1H.7 Status

Status: FAILED
Generated: {today}
Branch: {freezer.git_branch()}

## Scope

System A formal snapshot freezer / schema bridge only.

## Error

```text
{error_text}
```
"""
    freezer.write_text(outputs["report"], report)
    freezer.write_text(outputs["status"], status)


def print_result(result: freezer.FreezerResult) -> None:
    """Print the required lane summary."""
    print(f"1. status: {result.status}")
    print(f"2. candidate tables scanned: {result.candidate_tables_scanned}")
    print(f"3. best candidate path if any: {result.best_candidate_path or 'none'}")
    print(f"4. freeze mode: {result.freeze_mode}")
    print(
        "5. n_rows / n_prospective_rows / n_ge31 / n_ge33: "
        f"{result.n_rows or 'NA'} / {result.n_prospective_rows or 'NA'} / {result.n_ge31 or 'NA'} / {result.n_ge33 or 'NA'}"
    )
    print(f"6. schema status: {result.schema_status}")
    print(f"7. forbidden-column status: {result.forbidden_column_status}")
    print(f"8. downstream A-L1H.6 rerun command: {result.downstream_l1h6_rerun_command}")
    print("9. files created:")
    for path in result.output_paths:
        print(f"- {freezer.rel(path)}")


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description=(
            "Run A-L1H.7 formal snapshot freezer from an explicit YAML config. "
            "The default dry_run mode writes compact inventories, schema checks, "
            "manifests, validation rows, reports, and downstream instructions, "
            "but does not write formal snapshot rows."
        )
    )
    parser.add_argument("--config", default="configs/v11/systema_l1h7_formal_snapshot_freezer.yaml", help="A-L1H.7 freezer config path.")
    args = parser.parse_args()

    try:
        result = freezer.run_freezer(freezer.resolve_path(args.config))
    except Exception:
        error_text = traceback.format_exc()
        write_failure_outputs(args.config, error_text)
        print("1. status: FAILED")
        print("2. candidate tables scanned: 0")
        print("3. best candidate path if any: none")
        print("4. freeze mode: unknown")
        print("5. n_rows / n_prospective_rows / n_ge31 / n_ge33: NA / NA / NA / NA")
        print("6. schema status: FAILED")
        print("7. forbidden-column status: FAILED")
        print("8. downstream A-L1H.6 rerun command: python scripts/v11_l1h6_run_prospective_eval_harness.py --config configs/v11/systema_l1h6_prospective_eval_harness.yaml")
        print("9. files created: see FAILED status/report if written")
        print("[error]")
        print(error_text)
        return 1

    print_result(result)
    return 0 if result.status in {
        freezer.READY_STATUS,
        freezer.WAITING_STATUS,
        freezer.BLOCKED_SCHEMA_STATUS,
        freezer.BLOCKED_FORBIDDEN_STATUS,
        freezer.SNAPSHOT_FROZEN_PASS_STATUS,
    } else 1


if __name__ == "__main__":
    raise SystemExit(main())
