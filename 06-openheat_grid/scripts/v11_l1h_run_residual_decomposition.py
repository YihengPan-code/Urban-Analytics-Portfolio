#!/usr/bin/env python
"""Run A-L1H.0 residual decomposition and write the lane status file.

Inputs:
    - configs/v11/systema_l1h_residual_decomposition.yaml
    - Existing System A OOF prediction/model-score CSVs discovered by the
      decomposition script.

Outputs:
    - All residual decomposition CSV/Markdown outputs under
      outputs/v11_systema_l1_high_tail/residual_decomposition/
    - outputs/v11_systema_l1_high_tail/A_L1H_LANE_STATUS.md

Saved metrics:
    - Selected input inventory and residual summaries.
    - Fixed ge31 hit/miss/false-alarm row counts.
    - A cautious preliminary residual-pattern classification.

This runner does not stage, commit, train models, change formula-v2, calibrate
probabilities, or touch System B/SOLWEIG/archive collector outputs.
"""
from __future__ import annotations

import argparse
import subprocess
from datetime import date
from pathlib import Path
from typing import Any

import yaml

import v11_l1h_residual_decomposition as decomposition


ROOT = Path(__file__).resolve().parents[1]


def load_config(path: Path) -> dict[str, Any]:
    """Read the YAML config for the lane runner."""
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def git_branch() -> str:
    """Return current git branch if available."""
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() or "unknown"


def write_status(config_path: Path, config: dict[str, Any], result: decomposition.AnalysisResult) -> Path:
    """Write the lane status Markdown file."""
    status_path = ROOT / config["analysis"]["status_path"]
    status_path.parent.mkdir(parents=True, exist_ok=True)
    output_list = "\n".join(f"- `{decomposition.rel(path)}`" for path in result.output_paths)
    lines = [
        "# A-L1H Lane Status",
        "",
        f"Status: {result.status}",
        f"Generated: {date.today().isoformat()}",
        f"Branch: {git_branch()}",
        "",
        "## Scope",
        "",
        "A-L1H.0 residual decomposition only, using existing System A OOF predictions/model scores. No new models, formula-v2, probability calibration, high-tail regression, System B outputs, SOLWEIG outputs, or archive collector changes.",
        "",
        "## Commands run",
        "",
        f"- `python scripts/v11_l1h_run_residual_decomposition.py --config {decomposition.rel(config_path)}`",
        "",
        "## Files created / modified",
        "",
        output_list,
        f"- `{decomposition.rel(status_path)}`",
        "",
        "## Key results",
        "",
        f"- Selected input: `{result.selected_input}`",
        f"- Model(s): `{', '.join(result.selected_models)}`",
        f"- Target column: `{result.target_column}`",
        f"- Selected row count: {result.row_count}",
        f"- Station count: {result.station_count}",
        f"- Primary fixed ge31 observed / predicted: {result.observed_ge31_count} / {result.predicted_ge31_count}",
        f"- Primary ge31 hits / misses / false alarms: {result.ge31_hit_count} / {result.ge31_miss_count} / {result.ge31_false_alarm_count}",
        f"- Preliminary classification: {result.classification}",
        f"- Diagnostic caveat: {result.caveat}",
        "",
        "## Caveats",
        "",
        "- This is a retrospective OOF residual diagnostic, not a validated local 100m WBGT prediction system.",
        "- Fixed ge31 summaries are threshold diagnostics only and do not establish operational prospective forecast skill.",
        "- ge33 inventory is exploratory only.",
        "- Weather-regime decomposition is limited if weather variables are absent from the selected OOF prediction file.",
        "",
        "## Safe to commit",
        "",
        "- Config, scripts, protocol doc, and compact CSV/Markdown outputs under `outputs/v11_systema_l1_high_tail/` from this lane, subject to final changed-file review.",
        "",
        "## Not safe to commit",
        "",
        "- Any `data/solweig/`, `data/rasters/`, raw archive, `.tif`, `.tiff`, `svfs.zip`, patch zip packages, large hourly forecast CSV, System B outputs, SOLWEIG outputs, or unrelated existing modified `outputs/v11_level1/` files.",
        "",
        "## Next recommended action",
        "",
        decomposition.next_action_for(result.classification),
    ]
    status_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return status_path


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Run A-L1H.0 residual decomposition and lane status.")
    parser.add_argument("--config", default="configs/v11/systema_l1h_residual_decomposition.yaml")
    args = parser.parse_args()

    config_path = ROOT / args.config
    config = load_config(config_path)
    result = decomposition.write_outputs(config)
    status_path = write_status(config_path, config, result)
    print(f"[status] {result.status}")
    print(f"[status_path] {decomposition.rel(status_path)}")
    print(f"[selected_input] {result.selected_input}")
    print(f"[rows] {result.row_count}")
    print(f"[classification] {result.classification}")
    return 0 if result.status in {"PASS", "BLOCKED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
