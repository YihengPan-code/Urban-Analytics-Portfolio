#!/usr/bin/env python
"""Run the System A A-L1H.6 prospective evaluation harness.

Inputs:
    - configs/v11/systema_l1h6_prospective_eval_harness.yaml
    - Frozen A-L1H.5 contract artifacts and compact prospective snapshot
      candidates declared in the config.

Outputs:
    - Input inventory, expected schema, snapshot detection report, evaluation
      plan, metric schema, prospective metrics, station caveat refresh,
      promotion gate, English report, Chinese report, and status under
      configured paths.

Saved metrics:
    - Prospective support, fixed_31 baseline metrics, optional P_ge31
      calibration and policy metrics, optional expected exceedance / interval
      diagnostics, and station caveat refresh when a valid formal snapshot is
      present. No synthetic metrics are written while waiting for a snapshot.

This runner does not stage, commit, train models, touch System B or SOLWEIG
outputs, modify archive collectors, create station-adjusted WBGT, create local
100 m WBGT, create risk_score/hazard_score, or promote P_ge31 to an official
warning probability.
"""
from __future__ import annotations

import argparse
import traceback
from datetime import date

import v11_l1h6_prospective_eval_harness as harness


def write_failure_outputs(config_path: str, error_text: str) -> None:
    """Best-effort FAILED status writer for unexpected script errors."""
    try:
        config = harness.load_config(harness.resolve_path(config_path))
        outputs = config["outputs"]
        today = config.get("generated_date", date.today().isoformat())
        report = f"""# System A A-L1H.6 Prospective Evaluation Harness

Generated: {today}
Decision status: `FAILED`

The harness encountered an unexpected script error before completing outputs.

```text
{error_text}
```
"""
        status = f"""# A-L1H.6 Status

Status: FAILED
Generated: {today}
Branch: {harness.git_branch()}

## Scope

System A prospective evaluation harness only.

## Error

```text
{error_text}
```
"""
        harness.write_text(harness.resolve_path(outputs["report"]), report)
        harness.write_text(harness.resolve_path(outputs["status"]), status)
    except Exception:
        return


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description=(
            "Run A-L1H.6 prospective evaluation harness from an explicit YAML config. "
            "The command writes compact CSV/Markdown outputs and is safe when no formal snapshot exists."
        )
    )
    parser.add_argument("--config", default="configs/v11/systema_l1h6_prospective_eval_harness.yaml", help="A-L1H.6 harness config path.")
    args = parser.parse_args()

    try:
        result = harness.run_harness(harness.resolve_path(args.config))
    except Exception:
        error_text = traceback.format_exc()
        write_failure_outputs(args.config, error_text)
        print("[status] FAILED")
        print("[snapshot_found] no")
        print("[candidate_path] none")
        print("[n_rows] NA")
        print("[n_ge31] NA")
        print("[n_ge33] NA")
        print("[p_ge31_promotion_gate_status] P_GE31_NOT_PROMOTED")
        print("[ge33_status] P_GE33_REMAINS_EXPLORATORY")
        print("[station_caveat_headline] Script failed before station caveat refresh.")
        print("[error]")
        print(error_text)
        return 1

    print(f"[status] {result.status}")
    print(f"[snapshot_found] {'yes' if result.snapshot_found else 'no'}")
    print(f"[candidate_path] {result.candidate_path or 'none'}")
    print(f"[n_rows] {result.n_rows or 'NA'}")
    print(f"[n_ge31] {result.n_ge31 or 'NA'}")
    print(f"[n_ge33] {result.n_ge33 or 'NA'}")
    print(f"[p_ge31_promotion_gate_status] {result.p_ge31_promotion_gate_status}")
    print(f"[ge33_status] {result.ge33_status}")
    print(f"[station_caveat_headline] {result.station_caveat_headline}")
    print("[files_created]")
    for path in result.output_paths:
        print(f"- {harness.rel(path)}")
    return 0 if result.status in {harness.WAITING_STATUS, harness.PASS_STATUS, harness.WEAK_STATUS, harness.BLOCKED_SCHEMA_STATUS} else 1


if __name__ == "__main__":
    raise SystemExit(main())
