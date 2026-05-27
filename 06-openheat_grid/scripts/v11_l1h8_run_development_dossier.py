#!/usr/bin/env python
"""Run the System A A-L1H.8 development dossier generator.

Inputs:
    - configs/v11/systema_l1h8_development_dossier.yaml
    - Existing compact Markdown/status/report evidence declared in the config.

Outputs:
    - Development dossier CSV/Markdown artifacts under
      outputs/v11_systema_l1_high_tail/systema_development_dossier/
    - Chinese dossier doc under docs/v11/
    - Chinese frozen handoff doc under docs/handoff/

Saved metrics:
    - Dossier status, evidence artifact count, frozen System A state, formal
      snapshot waiting status, Level 2 boundary status, and future re-entry
      prompt path.

This runner does not stage, commit, train models, touch System B or SOLWEIG
outputs, modify archive collectors, create station-adjusted WBGT, create local
100 m WBGT, create official warning probability, create risk_score/hazard_score,
create System A/B coupling output, or create fake formal snapshot rows.
"""
from __future__ import annotations

import argparse
import traceback
from datetime import date

import v11_l1h8_systema_development_dossier as dossier


def write_failure_outputs(config_path: str, error_text: str) -> None:
    """Best-effort FAILED status writer for unexpected script errors."""
    try:
        config = dossier.load_config(dossier.resolve_path(config_path))
        outputs = config["outputs"]
        today = config.get("generated_date", date.today().isoformat())
        report = f"""# System A A-L1H.8 Development Dossier / Frozen Handoff

Generated: {today}
Decision status: `FAILED`

The dossier generator encountered an unexpected script error before completing outputs.

```text
{error_text}
```
"""
        status = f"""# A-L1H.8 Status

Status: FAILED
Generated: {today}
Branch: {dossier.git_branch()}

## Scope

System A development dossier and frozen handoff only.

## Error

```text
{error_text}
```
"""
        dossier.write_text(dossier.resolve_path(outputs["report"]), report)
        dossier.write_text(dossier.resolve_path(outputs["status"]), status)
    except Exception:
        return


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description=(
            "Run A-L1H.8 System A development dossier generation from an explicit YAML config. "
            "The command writes compact CSV/Markdown handoff outputs only."
        )
    )
    parser.add_argument("--config", default="configs/v11/systema_l1h8_development_dossier.yaml", help="A-L1H.8 dossier config path.")
    args = parser.parse_args()

    try:
        result = dossier.run_dossier(dossier.resolve_path(args.config))
    except Exception:
        error_text = traceback.format_exc()
        write_failure_outputs(args.config, error_text)
        print("[status] FAILED")
        print("[evidence_artifacts_inventoried] 0")
        print("[current_frozen_state] unknown")
        print("[formal_snapshot_waiting_status] unknown")
        print("[level2_boundary_status] unknown")
        print("[reentry_prompt_path] none")
        print("[docs_created] none")
        print("[error]")
        print(error_text)
        return 1

    print(f"[status] {result.status}")
    print(f"[evidence_artifacts_inventoried] {result.evidence_artifacts_inventoried}")
    print(f"[current_frozen_state] {result.current_frozen_state}")
    print(f"[formal_snapshot_waiting_status] {result.formal_snapshot_waiting_status}")
    print(f"[level2_boundary_status] {result.level2_boundary_status}")
    print(f"[reentry_prompt_path] {dossier.rel(result.reentry_prompt_path)}")
    print("[docs_created]")
    for path in result.docs_created:
        print(f"- {dossier.rel(path)}")
    print("[files_created]")
    for path in result.output_paths:
        print(f"- {dossier.rel(path)}")
    if result.missing_required_contract_sources:
        print("[missing_required_contract_sources]")
        for path in result.missing_required_contract_sources:
            print(f"- {dossier.rel(path)}")
    if result.missing_prior_artifacts:
        print("[missing_prior_artifacts]")
        for path in result.missing_prior_artifacts:
            print(f"- {dossier.rel(path)}")
    return 0 if result.status in {dossier.PASS_STATUS, dossier.PARTIAL_STATUS, dossier.BLOCKED_STATUS} else 1


if __name__ == "__main__":
    raise SystemExit(main())
